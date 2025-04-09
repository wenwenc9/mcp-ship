from fastapi import FastAPI, Query, Depends,Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import json

app = FastAPI()
# 新增中间件：用于打印请求信息
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # 获取客户端IP
    client_ip = request.client.host if request.client else "unknown"

    # 获取请求基本信息
    method = request.method
    url = request.url
    params = dict(request.query_params)

    # 获取请求体（仅处理JSON格式）
    body = {}
    try:
        body_bytes = await request.body()
        if body_bytes:
            body = await request.json()
    except json.JSONDecodeError:
        body = {"raw_body": body_bytes.decode()[:100]}  # 截取前100字符防止过大

    # 打印日志（可根据需要调整格式）
    print(f"""
    ┌───────────────────────────────
    │ 请求来自：{client_ip}
    │ 请求方法：{method}
    │ 请求接口：{url}
    │ URL参数：{params}
    │ 请求体：
    {json.dumps(body, indent=4, ensure_ascii=False)}
    └───────────────────────────────
    """)

    # 重新设置请求体以便后续处理
    request._body = body_bytes  # 类型: ignore

    # 继续处理请求
    response = await call_next(request)

    return response

# 模拟的港口基础资料数据
ports_data = {
    "上海": {"name": "上海 Port", "location": "China", "code": "SHA", 'port_id': '818239'},
    "纽约": {"name": "New York Port", "location": "USA", "code": "NYC", 'port_id': '639954'},
    "香港": {"name": "Hong Kong Port", "location": "China", "code": "HKG", 'port_id': '236938'}
}

# 模拟的船期数据
ship_schedules = [
    {'pol': '上海', 'pod': '纽约', 'departure_date': '2025-04-10', 'arrival_date': '2025-04-20',
     'pol_id': '818239', 'pod_id': '639954'},
    {'pol': '纽约', 'pod': '香港', 'departure_date': '2025-04-15', 'arrival_date': '2025-04-25',
     'pol_id': '703925', 'pod_id': '833021'},
    {'pol': '香港', 'pod': '上海', 'departure_date': '2025-04-20', 'arrival_date': '2025-04-30',
     'pol_id': '236938', 'pod_id': '380176'}
]


# 请求参数的 schemas
class PortInfoRequest(BaseModel):
    pol: Optional[str] = Field(
        None,
        description="起始港口名称（不区分大小写）",
        example="上海"
    )
    pod: Optional[str] = Field(
        None,
        description="目的港口名称（不区分大小写）",
        example="纽约"
    )


class ShipScheduleRequest(BaseModel):
    pol_id: str = Field(
        ...,
        description="起始港口ID（可从基础资料接口获取）",
        example="818239"
    )
    pod_id: str = Field(
        ...,
        description="目的港口ID（可从基础资料接口获取）",
        example="639954"
    )


# 响应的 schemas
class PortInfoResponse(BaseModel):
    message: str = Field(..., description="响应状态消息")
    pol: Optional[dict] = Field(None, description="起始港口详细信息")
    pod: Optional[dict] = Field(None, description="目的港口详细信息")

    class Config:
        schema_extra = {
            "example": {
                "message": "success",
                "pol": {
                    "name": "上海 Port",
                    "location": "China",
                    "code": "SHA",
                    "port_id": "818239"
                },
                "pod": {
                    "name": "New York Port",
                    "location": "USA",
                    "code": "NYC",
                    "port_id": "639954"
                }
            }
        }


class ShipScheduleResponse(BaseModel):
    message: Optional[str] = Field(None, description="错误信息（查询失败时返回）")
    data: Optional[List[dict]] = Field(None, description="船期列表（查询成功时返回）")

    class Config:
        schema_extra = {
            "example": {
                "data": [
                    {
                        "pol": "上海",
                        "pod": "纽约",
                        "departure_date": "2025-04-10",
                        "arrival_date": "2025-04-20",
                        "pol_id": "818239",
                        "pod_id": "639954"
                    }
                ]
            }
        }


@app.post("/ports/",
          response_model=PortInfoResponse,
          tags=["基础资料查询接口"],
          summary="查询港口基础信息",
          description="根据港口名称查询POL（起运港）和POD（目的港）的详细信息，至少需要提供一个港口名称",
          responses={
              200: {"description": "成功获取港口信息"},
              400: {"description": "缺少必要参数"},
              404: {"description": "未找到指定港口"}
          })
async def get_port_info(request: PortInfoRequest):
    """
    港口基础资料查询接口，支持以下场景：
    - 同时查询POL和POD信息
    - 单独查询POL或POD信息

    参数要求：
    - 至少提供pol或pod中的一个参数
    - 港口名称不区分大小写
    """
    result = {"message": ""}

    # 参数校验
    if not request.pol and not request.pod:
        result["message"] = "必须提供至少一个港口参数（pol或pod）"
        return JSONResponse(status_code=400, content=result)

    not_found_flag = False
    not_found_messages = []

    # 处理POL查询
    if request.pol:
        pol_key = request.pol.lower()
        if pol_key in ports_data:
            result["pol"] = ports_data[pol_key]
        else:
            not_found_flag = True
            not_found_messages.append(f"POL '{request.pol}'")

    # 处理POD查询
    if request.pod:
        pod_key = request.pod.lower()
        if pod_key in ports_data:
            result["pod"] = ports_data[pod_key]
        else:
            not_found_flag = True
            not_found_messages.append(f"POD '{request.pod}'")

    # 处理未找到的情况
    if not_found_flag:
        result["message"] = "未找到以下港口: " + ", ".join(not_found_messages)
        return JSONResponse(status_code=404, content=result)

    result["message"] = "success"
    return JSONResponse(status_code=200, content=result)


@app.post("/ship_schedules/",
          response_model=ShipScheduleResponse,
          tags=["船期查询接口"],
          summary="查询船期信息",
          description="根据港口ID查询两点之间的船期信息",
          responses={
              200: {"description": "成功获取船期数据"},
              404: {"description": "未找到匹配船期"}
          })
async def get_ship_schedule(request: ShipScheduleRequest):
    """
    船期查询接口主要功能：
    - 根据精确的港口ID对查询船期
    - 返回匹配的船期列表（包含船期详细信息）
    - 支持精确的港口ID匹配

    典型应用场景：
    1. 先通过基础资料接口获取港口ID
    2. 使用获取的港口ID查询具体船期
    """
    schedules = [schedule for schedule in ship_schedules
                 if schedule["pol_id"] == request.pol_id
                 and schedule["pod_id"] == request.pod_id]

    if schedules:
        return JSONResponse(status_code=200, content={"data": schedules})

    return JSONResponse(
        status_code=404,
        content={"message": f"未找到{request.pol_id}到{request.pod_id}的船期"}
    )


# 挂载MCP服务
from fastapi_mcp import add_mcp_server

add_mcp_server(
    app,
    mount_path="/sse",
    name="物流可视化平台MCP服务",
    description="提供港口基础资料和船期查询的标准化接口服务",
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)