import time
from pathlib import Path
from datetime import datetime

import rich
import shortuuid
from PIL import Image, UnidentifiedImageError
from mineru_vl_utils import MinerUClient


from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form, status
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)

from utils import check_mimetype, convert_to_images
from schemas import OutputFormats, PageResults, OnePageResult

# 初始化 MinerUClient
client = MinerUClient(
    backend="http-client",server_url="http://127.0.0.1:9001",max_concurrency=200,)

app = FastAPI(
    debug=False,
    title="MinerU2.5-2509",
    redoc_url=None,
    docs_url=None,
    redirect_slashes=False,
)
app.mount("/static", StaticFiles(directory=Path("static/")),name="static")


@app.get("/docs", include_in_schema=False)
async def custom_docs():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url=f"/static/swagger-ui-bundle.js",
        swagger_css_url=f"/static/swagger-ui.css",
    )

@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()

@app.get("/redoc",include_in_schema=False)
async def custom_redoc():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url=f"/static/redoc.standalone.js",
    )


@app.post("/extract/", response_model=PageResults)
async def extract_blocks_from_image(
    request:Request,
    request_id:str = Form(default_factory=shortuuid.uuid),
    output_format:OutputFormats = Form(
        default=OutputFormats.JSON,
        title="输出格式",
        description=f"返回格式：支持['markdown', 'json']；",
    ),
    file: UploadFile = File(
        ...,
        title="上传文件",
        description="仅支持pdf,jpg,png；上传的文件最好列明文件名"),
):
    """接收上传的图片文件，并提取其中的信息块。"""
    now_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("[%s] request received, request_id: %s" % (now_time,request_id))
    try:
        file_type = check_mimetype(content_type=file.content_type,filename=file.filename)
        list_of_extracted_blocks=None
        image_lists = await convert_to_images(await file.read(), file_type)
        start_time = time.time()
        list_of_page_results = await client.aio_batch_two_step_extract(image_lists)
        end_time = time.time()

        page_results:list[OnePageResult]=list()
        for result in list_of_page_results:
            page_result = OnePageResult.model_validate(dict(content_blocks=result))
            if output_format.value == 'markdown':
                markdown_content = "\n".join(
                    [ block.type.renderer(block.content) for block in page_result.content_blocks ])
                page_result.markdown_content = markdown_content
                page_result.content_blocks = None
            page_results.append(page_result)
        page_results = PageResults.model_validate(dict(list_of_extracted_pages=page_results))

    except AssertionError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc))
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot identify upload image. Maybe broken..")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    else:
        # 打印提取结果和耗时（可选）
        # rich.print(extracted_response)
        print(f"[request_id: {request_id}] Time consumed: {end_time - start_time:.2f} seconds")

    return page_results

# 可选：添加一个根路由用于测试服务是否正常运行
@app.get("/")
def read_root():
    return {"message": "Welcome to the MinerU2.5 API!"}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=8999)
