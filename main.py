from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import psutil
from hurry.filesize import size, alternative
import platform
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
 
limiter = Limiter(key_func=get_remote_address)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = [
    "http://localhost:3000",
    "http://raspberrypi.local:8441",
    "http://pi.joelspi.org",
    "https://pi.joelspi.org"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/stats")
@limiter.limit("100/minute")
async def getStats(request: Request):
    return {
        "cpuTemp": getCpuTemp(),
        "cpuPercent": getCpuPercent(),
        "diskUsage": getDiskUsage(),
        "memUsage": getMemoryUsage(),
        "os": getOsInfo()
    }

def getCpuTemp():
    return psutil.sensors_temperatures().get("cpu_thermal")[0].current

def getCpuPercent():
    return psutil.cpu_percent(percpu=True)

def getDiskUsage():
    usage = psutil.disk_usage('/')
    return {
        "total": bytesConvert(usage.total, "gb"), 
        "used": bytesConvert(usage.used, "gb"),
        "free": bytesConvert(usage.free, "gb"),
        "percent": usage.percent
    }
    
def getMemoryUsage():
    usage = psutil.virtual_memory()
    return {
        "total": bytesConvert(usage.total, "mb"),
        "used": bytesConvert(usage.used, "mb"),
        "free": bytesConvert(usage.available,"mb"),
        "percent": usage.percent
    }
    
def getOsInfo():
    return {
        "hostname": platform.node(),
        "platform": platform.system(),
        "arch": platform.machine()
    }
    
def bytesConvert(bytes, type):
    match type:
        case "mb":
            return round(bytes / 1024 / 1024)
        case "gb":
            return round(bytes / 1024 / 1024 / 1024)
    return round(bytes / 1048576)
