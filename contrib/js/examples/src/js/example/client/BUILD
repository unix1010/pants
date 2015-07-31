js_library(
  name='client',
  dependencies=[
    '3rdparty/js/react',
    'contrib/js/examples/src/js/example/ui'
  ],
  resources=rglobs('src/*.css')
)

npm_module(
  name='client-binary',
  entry='main.jsx',
  dependencies=[':client']
)
