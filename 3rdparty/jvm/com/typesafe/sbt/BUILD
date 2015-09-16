jar_library(
  name='incremental-compiler',
  jars=[
    # NB: when this is bumped past 0.13.10, please see:
    #   https://rbcommons.com/s/twitter/r/2810/
    jar(org='org.scala-sbt', name='compiler-integration', rev='0.13.10-stuhood-java-invalidation-repro-1441992827'),
  ],
  dependencies=[
    '//:scala-compiler',
    '//:scala-library',
  ],
)
