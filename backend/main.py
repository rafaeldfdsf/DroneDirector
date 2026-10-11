import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.projects import router
from config import CORS_ORIGINS
from services.ai_scorer import MODEL_NAME, check_model_files

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
app = FastAPI(title='DroneDirector', version='0.1.0', description='Montagem local de filmagens de drone.')
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=['GET', 'POST'],
                   allow_headers=['Content-Type', 'Range'], expose_headers=['Content-Range', 'Content-Disposition'])
app.include_router(router)


@app.get('/api/ai/status')
def ai_status() -> dict:
    try:
        check_model_files()
        return {'ready': True, 'mode': 'local', 'model': MODEL_NAME, 'device': 'CPU',
                'message': 'IA local instalada. Os vídeos ficam neste computador.'}
    except ValueError as error:
        return {'ready': False, 'mode': 'local', 'model': MODEL_NAME, 'device': 'CPU', 'message': str(error)}


@app.get('/api/health')
def health() -> dict:
    return {'status': 'ok'}


@app.exception_handler(Exception)
async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
    logging.getLogger(__name__).error('Erro em %s', request.url.path, exc_info=error)
    return JSONResponse(status_code=500, content={'detail': 'Ocorreu um erro no backend. Consulta o terminal.'})


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
    logging.getLogger(__name__).info('Dados inválidos em %s: %s', request.url.path, error.errors())
    return JSONResponse(status_code=422, content={
        'detail': 'Os dados enviados não são válidos. Verifica os vídeos e escolhe uma duração de 15, 30 ou 60 segundos.'})
