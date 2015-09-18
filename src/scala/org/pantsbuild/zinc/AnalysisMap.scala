/**
 * Copyright (C) 2015 Pants project contributors (see CONTRIBUTORS.md).
 * Licensed under the Apache License, Version 2.0 (see LICENSE).
 */

package org.pantsbuild.zinc

import java.io.{
  File,
  IOException
}

import sbt.{
  CompileSetup,
  IO
}
import sbt.inc.{
  Analysis,
  AnalysisStore,
  FileBasedStore,
  Locate
}
import xsbti.{
  FileRef,
  FileRefJarred,
  FileRefLoose
}

import org.pantsbuild.zinc.cache.Cache
import org.pantsbuild.zinc.cache.Cache.Implicits

/**
 * A facade around the analysis cache to:
 *   1) map between classpath entries and cache locations
 *   2) use analysis for `definesClass` when it is available
 *
 * SBT uses the `definesClass` and `getAnalysis` methods in order to load the APIs for upstream
 * classes. For a classpath containing multiple entries, sbt will call `definesClass` sequentially
 * on classpath entries until it finds a classpath entry defining a particular class. When it finds
 * the appropriate classpath entry, it will use `getAnalysis` to fetch the API for that class.
 */
case class AnalysisMap private[AnalysisMap] (
  // a map of classpath entries to cache file fingerprints, excluding the current compile destination
  analysisLocations: Map[File, FileFPrint]
) {
  /**
   * An implementation of definesClass that will use analysis for an input directory to determine
   * whether it defines a particular class.
   */
  def definesClass(classpathEntry: File): String => Option[FileRef] =
    getAnalysis(classpathEntry).map { analysis =>
      // strongly hold the classNames, and transform them to ensure that they are unlinked from
      // the remainder of the analysis
      AnalysisMap.RefConstructor(
        classpathEntry,
        analysis.relations.classes.reverseMap.keys.toList.toSet
      )
    }.getOrElse {
      // no analysis: return a function that will scan instead
      Locate.definesClass(classpathEntry)
    }

  /**
   * Gets analysis for a classpath entry (if it exists) by translating its path to a potential
   * cache location and then checking the cache.
   */
  def getAnalysis(classpathEntry: File): Option[Analysis] =
    analysisLocations.get(classpathEntry).flatMap(AnalysisMap.get)
}

object AnalysisMap {
  /**
   * Static cache for compile analyses. Values must be Options because in get() we don't yet
   * know if, on a cache miss, the underlying file will yield a valid Analysis.
   */
  private val analysisCache =
    Cache[FileFPrint, Option[(Analysis, CompileSetup)]](Setup.Defaults.analysisCacheLimit)

  /**
   * Given a map of classpath entries to cache file locations, hashes the inputs and returns an
   * AnalysisMap that requires fingerprint matches.
   */
  def create(analysisLocations: Map[File, File]): AnalysisMap =
    AnalysisMap(
      // create fingerprints for all inputs at startup
      analysisLocations.flatMap {
        case (classpathEntry, cacheFile) => FileFPrint.fprint(cacheFile).map(classpathEntry -> _)
      }
    )

  private def get(cacheFPrint: FileFPrint): Option[Analysis] =
    analysisCache.getOrElseUpdate(cacheFPrint) {
      // re-fingerprint the file on miss, to ensure that analysis hasn't changed since we started
      if (!FileFPrint.fprint(cacheFPrint.file).exists(_ == cacheFPrint)) {
        throw new IOException(s"Analysis at $cacheFPrint has changed since startup!")
      }
      FileBasedStore(cacheFPrint.file).get
    }.map(_._1)

  /**
   * Create an analysis store backed by analysisCache.
   */
  def cachedStore(cacheFile: File): AnalysisStore = {
    val fileStore = AnalysisStore.cached(FileBasedStore(cacheFile))

    val fprintStore = new AnalysisStore {
      def set(analysis: Analysis, setup: CompileSetup) {
        fileStore.set(analysis, setup)
        FileFPrint.fprint(cacheFile) foreach { analysisCache.put(_, Some((analysis, setup))) }
      }
      def get(): Option[(Analysis, CompileSetup)] = {
        FileFPrint.fprint(cacheFile) flatMap { fprint =>
          analysisCache.getOrElseUpdate(fprint) {
            fileStore.get
          }
        }
      }
    }

    AnalysisStore.sync(AnalysisStore.cached(fprintStore))
  }

  /**
   * A constructor of FileRefs for the given classpath entry.
   */
  case class RefConstructor(classpathEntry: File, classNames: Set[String]) extends (String => Option[FileRef]) {
    private final val refImpl =
      if (classpathEntry.getName.endsWith(".jar")) {
        p: String => new FileRefJarred(classpathEntry, p)
      } else {
        p: String => new FileRefLoose(new File(p))
      }

    def apply(className: String): Option[FileRef] =
      if (classNames(className)) {
        Some(refImpl(IO.classfilePathForClassname(className)))
      } else {
        None
      }
  }
}
