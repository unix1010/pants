package org.pantsbuild.example.repro;

import scala.Option;
import com.twitter.io.Buf;
import com.twitter.io.Bufs;

public class Repro {
  private static Buf getOwnBuf() {
    return new Buf() {
      @Override
      public void write(byte[] output, int off) throws IllegalArgumentException {
        // do nothing
      }

      @Override
      public void write(java.nio.ByteBuffer buffer) {
        // do nothing
      }

      @Override
      public Option<ByteArray> unsafeByteArrayBuf() {
        return Option.apply(null);
      }

      @Override
      public int length() {
        return 0;
      }

      @Override
      public Buf slice(int from, int until) {
        return Bufs.EMPTY;
      }

      @Override
      public byte get(int index) {
        return 0;
      }

      @Override
      public int process(int from, int until, Processor processor) {
        return 0;
      }
    };
  }

  public static void main(String[] args) {
    Buf buf = getOwnBuf();
    System.out.println("Made a buf: " + buf);
  }
}
