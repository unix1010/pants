// Copyright 2017 Pants project contributors (see CONTRIBUTORS.md).
// Licensed under the Apache License, Version 2.0 (see LICENSE).

use bazel_protos;
use boxfuture::{Boxable, BoxFuture};
use futures;
use futures::Future;
use futures::future::join_all;
use itertools::Itertools;
use {Digest, File, FileContent, PathStat, Store};
use hash::Fingerprint;
use protobuf;
use std::ffi::OsString;
use std::fmt;
use std::path::PathBuf;
use std::sync::Arc;

#[derive(Clone, PartialEq)]
pub struct Snapshot {
  pub digest: Digest,
  pub path_stats: Vec<PathStat>,
}

pub trait GetFileDigest<Error> {
  fn digest(&self, file: &File) -> BoxFuture<Digest, Error>;
}

impl Snapshot {
  pub fn from_path_stats<
    GFD: GetFileDigest<Error> + Sized + Clone,
    Error: fmt::Debug + 'static + Send,
  >(
    store: Arc<Store>,
    file_digester: GFD,
    mut path_stats: Vec<PathStat>,
  ) -> BoxFuture<Snapshot, String> {
    path_stats.sort_by(|a, b| a.path().cmp(b.path()));
    Snapshot::from_sorted_path_stats(store, file_digester, path_stats)
  }

  fn from_sorted_path_stats<
    GFD: GetFileDigest<Error> + Sized + Clone,
    Error: fmt::Debug + 'static + Send,
  >(
    store: Arc<Store>,
    file_digester: GFD,
    path_stats: Vec<PathStat>,
  ) -> BoxFuture<Snapshot, String> {
    let mut file_futures: Vec<BoxFuture<bazel_protos::remote_execution::FileNode, String>> =
      Vec::new();
    let mut dir_futures: Vec<BoxFuture<bazel_protos::remote_execution::DirectoryNode, String>> =
      Vec::new();

    for (first_component, group) in
      &path_stats.iter().cloned().group_by(|s| {
        s.path().components().next().unwrap().as_os_str().to_owned()
      })
    {
      let mut path_group: Vec<PathStat> = group.collect();
      if path_group.len() == 1 && path_group.get(0).unwrap().path().components().count() == 1 {
        // Exactly one entry with exactly one component indicates either a file in this directory,
        // or an empty directory.
        // If the child is a non-empty directory, or a file therein, there must be multiple
        // PathStats with that prefix component, and we will handle that in the recursive
        // save_directory call.

        match path_group.pop().unwrap() {
          PathStat::File { ref stat, .. } => {
            let is_executable = stat.is_executable;
            file_futures.push(
              file_digester
                .clone()
                .digest(&stat)
                .map_err(|e| format!("{:?}", e))
                .and_then(move |digest| {
                  let mut file_node = bazel_protos::remote_execution::FileNode::new();
                  file_node.set_name(osstring_as_utf8(first_component)?);
                  file_node.set_digest(digest.into());
                  file_node.set_is_executable(is_executable);
                  Ok(file_node)
                })
                .to_boxed(),
            );
          }
          PathStat::Dir { .. } => {
            // Because there are no children of this Dir, it must be empty.
            dir_futures.push(
              store
                .record_directory(&bazel_protos::remote_execution::Directory::new())
                .map(move |digest| {
                  let mut directory_node = bazel_protos::remote_execution::DirectoryNode::new();
                  directory_node.set_name(osstring_as_utf8(first_component).unwrap());
                  directory_node.set_digest(digest.into());
                  directory_node
                })
                .to_boxed(),
            );
          }
        }
      } else {
        dir_futures.push(
          // TODO: Memoize this in the graph
          Snapshot::from_sorted_path_stats(
            store.clone(),
            file_digester.clone(),
            paths_of_child_dir(path_group),
          ).and_then(move |snapshot| {
            let mut dir_node = bazel_protos::remote_execution::DirectoryNode::new();
            dir_node.set_name(osstring_as_utf8(first_component)?);
            dir_node.set_digest(snapshot.digest.into());
            Ok(dir_node)
          })
            .to_boxed(),
        );
      }
    }
    join_all(dir_futures)
      .join(join_all(file_futures))
      .and_then(move |(dirs, files)| {
        let mut directory = bazel_protos::remote_execution::Directory::new();
        directory.set_directories(protobuf::RepeatedField::from_vec(dirs));
        directory.set_files(protobuf::RepeatedField::from_vec(files));
        store.record_directory(&directory).map(move |digest| {
          Snapshot {
            digest: digest,
            path_stats: path_stats,
          }
        })
      })
      .to_boxed()
  }

  pub fn contents(self, store: Arc<Store>) -> BoxFuture<Vec<FileContent>, String> {
    Snapshot::contents_for_directory_helper(self.digest.0, store, PathBuf::from(""))
      .map(|mut v| {
        v.sort_by(|a, b| a.path.cmp(&b.path));
        v
      })
      .to_boxed()
  }

  // Assumes that all fingerprints it encounters are valid.
  // Returns an unsorted Vec.
  fn contents_for_directory_helper(
    fingerprint: Fingerprint,
    store: Arc<Store>,
    path_so_far: PathBuf,
  ) -> BoxFuture<Vec<FileContent>, String> {
    store
      .load_directory_proto(fingerprint)
      .and_then(move |maybe_dir| {
        maybe_dir.ok_or_else(|| {
          format!("Could not find directory with fingerprint {}", fingerprint)
        })
      })
      .and_then(move |dir| {
        let file_futures = join_all(
          dir
            .get_files()
            .iter()
            .map(|file_node| {
              let path = path_so_far.join(file_node.get_name());
              let maybe_bytes =
                store.load_file_bytes(
                  Fingerprint::from_hex_string(file_node.get_digest().get_hash()).unwrap(),
                );
              futures::future::ok(path).join(maybe_bytes)
            })
            .collect::<Vec<_>>(),
        );
        let dir_futures = join_all(
          dir
            .get_directories()
            .iter()
            .map(|dir_node| {
              Snapshot::contents_for_directory_helper(
                Fingerprint::from_hex_string(dir_node.get_digest().get_hash()).unwrap(),
                store.clone(),
                path_so_far.join(dir_node.get_name()),
              )
            })
            .collect::<Vec<_>>(),
        );
        file_futures.join(dir_futures)
      })
      .and_then(
        move |(paths_and_maybe_byteses, dirs): (Vec<(PathBuf, Option<Vec<u8>>)>,
                                                Vec<Vec<FileContent>>)| {
          join_all(
            paths_and_maybe_byteses
              .into_iter()
              .map(|(path, maybe_bytes)| {
                maybe_bytes
                  .ok_or_else(|| format!("Couldn't find file contents for {:?}", path))
                  .map(|content| FileContent { path, content })
              })
              .collect::<Vec<Result<FileContent, _>>>(),
          ).join(futures::future::ok(dirs))
        },
      )
      .map(|(mut files, dirs)| {
        for mut dir in dirs.into_iter() {
          files.append(&mut dir)
        }
        files
      })
      .to_boxed()
  }
}

impl fmt::Debug for Snapshot {
  fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
    write!(
      f,
      "Snapshot(digest={:?}, entries={})",
      self.digest,
      self.path_stats.len()
    )
  }
}

fn paths_of_child_dir(paths: Vec<PathStat>) -> Vec<PathStat> {
  paths
    .into_iter()
    .filter_map(|s| {
      if s.path().components().count() == 1 {
        return None;
      }
      Some(match s {
        PathStat::File { path, stat } => {
          PathStat::File {
            path: path.iter().skip(1).collect(),
            stat: stat,
          }
        }
        PathStat::Dir { path, stat } => {
          PathStat::Dir {
            path: path.iter().skip(1).collect(),
            stat: stat,
          }
        }
      })
    })
    .collect()
}

fn osstring_as_utf8(path: OsString) -> Result<String, String> {
  path.into_string().map_err(|p| {
    format!("{:?}'s file_name is not representable in UTF8", p)
  })
}

#[cfg(test)]
mod tests {
  extern crate testutil;
  extern crate tempdir;

  use boxfuture::{BoxFuture, Boxable};
  use futures::future::Future;
  use tempdir::TempDir;
  use self::testutil::make_file;

  use super::super::{Digest, File, Fingerprint, GetFileDigest, PathGlobs, PathStat, PosixFS,
                     ResettablePool, Snapshot, Store, VFS};

  use std;
  use std::error::Error;
  use std::path::PathBuf;
  use std::sync::Arc;

  const AGGRESSIVE: &str = "Aggressive";
  const LATIN: &str = "Chaetophractus villosus";
  const STR: &str = "European Burmese";

  fn setup() -> (Arc<Store>, TempDir, Arc<PosixFS>, FileSaver) {
    let pool = Arc::new(ResettablePool::new("test-pool-".to_string()));
    let store = Arc::new(
      Store::new(TempDir::new("lmdb_store").unwrap(), pool.clone()).unwrap(),
    );
    let dir = TempDir::new("root").unwrap();
    let posix_fs = Arc::new(PosixFS::new(dir.path(), pool, vec![]).unwrap());
    let digester = FileSaver(store.clone(), posix_fs.clone());
    (store, dir, posix_fs, digester)
  }

  #[test]
  fn snapshot_one_file() {
    let (store, dir, posix_fs, digester) = setup();

    let file_name = PathBuf::from("roland");
    make_file(&dir.path().join(&file_name), STR.as_bytes(), 0o600);

    let path_stats = expand_all_sorted(posix_fs);
    assert_eq!(
      Snapshot::from_path_stats(store, digester, path_stats.clone())
        .wait()
        .unwrap(),
      Snapshot {
        digest: Digest(
          Fingerprint::from_hex_string(
            "63949aa823baf765eff07b946050d76ec0033144c785a94d3ebd82baa931cd16",
          ).unwrap(),
          80,
        ),
        path_stats: path_stats,
      }
    );
  }

  #[test]
  fn snapshot_recursive_directories() {
    let (store, dir, posix_fs, digester) = setup();

    let cats = PathBuf::from("cats");
    let roland = cats.join("roland");
    std::fs::create_dir_all(&dir.path().join(cats)).unwrap();
    make_file(&dir.path().join(&roland), STR.as_bytes(), 0o600);

    let path_stats = expand_all_sorted(posix_fs);
    assert_eq!(
      Snapshot::from_path_stats(store, digester, path_stats.clone())
        .wait()
        .unwrap(),
      Snapshot {
        digest: Digest(
          Fingerprint::from_hex_string(
            "8b1a7ea04eaa2527b35683edac088bc826117b53b7ec6601740b55e20bce3deb",
          ).unwrap(),
          78,
        ),
        path_stats: path_stats,
      }
    );
  }

  #[test]
  fn snapshot_recursive_directories_including_empty() {
    let (store, dir, posix_fs, digester) = setup();

    let cats = PathBuf::from("cats");
    let roland = cats.join("roland");
    let dogs = PathBuf::from("dogs");
    let llamas = PathBuf::from("llamas");
    std::fs::create_dir_all(&dir.path().join(&cats)).unwrap();
    std::fs::create_dir_all(&dir.path().join(&dogs)).unwrap();
    std::fs::create_dir_all(&dir.path().join(&llamas)).unwrap();
    make_file(&dir.path().join(&roland), STR.as_bytes(), 0o600);

    let sorted_path_stats = expand_all_sorted(posix_fs);
    let mut unsorted_path_stats = sorted_path_stats.clone();
    unsorted_path_stats.reverse();
    assert_eq!(
      Snapshot::from_path_stats(store, digester, unsorted_path_stats)
        .wait()
        .unwrap(),
      Snapshot {
        digest: Digest(
          Fingerprint::from_hex_string(
            "fbff703bdaac62accf2ea5083bcfed89292073bf710ef9ad14d9298c637e777b",
          ).unwrap(),
          232,
        ),
        path_stats: sorted_path_stats,
      }
    );
  }

  #[test]
  fn contents_for_one_file() {
    let (store, dir, posix_fs, digester) = setup();

    let file_name = PathBuf::from("roland");
    make_file(&dir.path().join(&file_name), STR.as_bytes(), 0o600);

    let contents = Snapshot::from_path_stats(store.clone(), digester, expand_all_sorted(posix_fs))
      .wait()
      .unwrap()
      .contents(store)
      .wait()
      .unwrap();
    // TODO: Write helper for asserting equality of FileContents (and Vecs thereof).
    assert_eq!(contents.len(), 1);
    assert_eq!(contents.get(0).unwrap().path, file_name);
    assert_eq!(contents.get(0).unwrap().content, STR.as_bytes().to_vec());
  }

  #[test]
  fn contents_for_files_in_multiple_directories() {
    let (store, dir, posix_fs, digester) = setup();

    let armadillos = PathBuf::from("armadillos");
    let armadillos_abs = dir.path().join(&armadillos);
    std::fs::create_dir_all(&armadillos_abs).unwrap();
    let amy = armadillos.join("amy");
    make_file(&dir.path().join(&amy), LATIN.as_bytes(), 0o600);
    let rolex = armadillos.join("rolex");
    make_file(&dir.path().join(&rolex), AGGRESSIVE.as_bytes(), 0o600);

    let cats = PathBuf::from("cats");
    let cats_abs = dir.path().join(&cats);
    std::fs::create_dir_all(&cats_abs).unwrap();
    let roland = cats.join("roland");
    make_file(&dir.path().join(&roland), STR.as_bytes(), 0o600);

    let dogs = PathBuf::from("dogs");
    let dogs_abs = dir.path().join(&dogs);
    std::fs::create_dir_all(&dogs_abs).unwrap();

    let path_stats_sorted = expand_all_sorted(posix_fs);
    let mut path_stats_reversed = path_stats_sorted.clone();
    path_stats_reversed.reverse();
    let contents = Snapshot::from_path_stats(store.clone(), digester, path_stats_reversed)
      .wait()
      .unwrap()
      .contents(store)
      .wait()
      .unwrap();
    // TODO: Write helper for asserting equality of FileContents (and Vecs thereof).
    assert_eq!(contents.len(), 3);
    assert_eq!(contents.get(0).unwrap().path, amy);
    assert_eq!(contents.get(0).unwrap().content, LATIN.as_bytes().to_vec());
    assert_eq!(contents.get(1).unwrap().path, rolex);
    assert_eq!(
      contents.get(1).unwrap().content,
      AGGRESSIVE.as_bytes().to_vec()
    );
    assert_eq!(contents.get(2).unwrap().path, roland);
    assert_eq!(contents.get(2).unwrap().content, STR.as_bytes().to_vec());
  }

  #[derive(Clone)]
  struct FileSaver(Arc<Store>, Arc<PosixFS>);

  impl GetFileDigest<String> for FileSaver {
    fn digest(&self, file: &File) -> BoxFuture<Digest, String> {
      let file_copy = file.clone();
      let store = self.0.clone();
      self
        .1
        .clone()
        .read_file(&file)
        .map_err(move |err| {
          format!("Error reading file {:?}: {}", file_copy, err.description())
        })
        .and_then(move |content| store.store_file_bytes(content.content))
        .to_boxed()
    }
  }

  fn expand_all_sorted(posix_fs: Arc<PosixFS>) -> Vec<PathStat> {
    let mut v = posix_fs
      .expand(PathGlobs::create(&["**".to_owned()], &vec![]).unwrap())
      .wait()
      .unwrap();
    v.sort_by(|a, b| a.path().cmp(b.path()));
    v
  }
}
