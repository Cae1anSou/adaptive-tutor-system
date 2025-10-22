import { generateService } from '@umijs/openapi'

generateService({
  requestLibPath: "import request from '@/request'",
  schemaPath: 'http://localhost:8000/api/v1/openapi.json',
  serversPath: './src',
})
