from fastapi import FastAPI, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List

app = FastAPI()

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
    pol: Optional[str] = Field(None, description="起始港口的名称")
    pod: Optional[str] = Field(None, description="目的港口的名称")


class ShipScheduleRequest(BaseModel):
    pol_id: str = Field(..., description="起始港 id")
    pod_id: str = Field(..., description="目的港 id")


# 响应的 schemas
class PortInfoResponse(BaseModel):
    message: str = Field(..., description="响应消息")
    pol: Optional[dict] = Field(None, description="起始港口信息")
    pod: Optional[dict] = Field(None, description="目的港口信息")


class ShipScheduleResponse(BaseModel):
    message: Optional[str] = Field(None, description="响应消息")
    data: Optional[List[dict]] = Field(None, description="船期数据")


# 查询港口基础资料
@app.get("/ports/", response_model=PortInfoResponse, tags=["基础资料查询接口"])
async def get_port_info(request: PortInfoRequest = Depends()):
    """
    查询港口基础资料
    :param request: 请求参数
    :return: 港口基础资料
    """
    result = {
        "message": "",
    }
    # --- 检测
    if not request.pol and not request.pod:
        result.update(message="查询船期需要明确起始港到目的港，如：盐田到洛杉矶")
        return JSONResponse(status_code=201, content=result)

    # --- 查找
    not_founc_flag = False
    if request.pol:
        request.pol = request.pol.lower()
        if request.pol in ports_data:
            result["pol"] = ports_data[request.pol]
        else:
            not_founc_flag = True
            result["message"] = f"POL '{request.pol}' 在基础资料数据库无法找到"

    if request.pod:
        request.pod = request.pod.lower()
        if request.pod in ports_data:
            result["pod"] = ports_data[request.pod]
        else:
            not_founc_flag = True
            result["message"] += f" POD '{request.pod}' 在基础资料数据库无法找到"
    if not_founc_flag:
        return JSONResponse(status_code=202, content=result)

    return JSONResponse(status_code=200, content=result)


# 查询船期数据
@app.get("/ship_schedules/", response_model=ShipScheduleResponse, tags=["船期查询接口"])
async def get_ship_schedule(request: ShipScheduleRequest = Depends()):
    """
    查询船期数据
    :param request: 请求参数
    :return: 船期数据
    """
    schedules = [schedule for schedule in ship_schedules if
                 schedule["pol_id"] == request.pol_id and schedule["pod_id"] == request.pod_id]
    if schedules:
        return JSONResponse(status_code=200, content={"data": schedules})
    else:
        return JSONResponse(status_code=201, content={"message": "查无数据"})


# 将 FastAPI 应用挂载为 MCP 服务器
from fastapi_mcp import add_mcp_server
add_mcp_server(
    app,
    mount_path="/mcp",  # MCP 服务器挂载路径
    name="Ports API MCP",  # MCP 服务器名称
    base_url="127.0.0.1:8000"
    # describe_all_responses=True,
    # describe_full_response_schema=True
)


# 启动应用
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)