from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import psutil
import platform
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_ipaddr
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_ipaddr)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = [
    "http://localhost:3000",
    "http://raspberrypi.local:8441",
    "http://pi.joelspi.org",
    "https://pi.joelspi.org",
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
        "os": getOsInfo(),
    }


def getCpuTemp():
    return psutil.sensors_temperatures().get("cpu_thermal")[0].current


def getCpuPercent():
    return psutil.cpu_percent(percpu=True)


def getDiskUsage():
    usage = psutil.disk_usage("/")
    return {
        "total": bytesConvert(usage.total, "gb"),
        "used": bytesConvert(usage.used, "gb"),
        "free": bytesConvert(usage.free, "gb"),
        "percent": usage.percent,
    }


def getMemoryUsage():
    usage = psutil.virtual_memory()
    return {
        "total": bytesConvert(usage.total, "mb"),
        "used": bytesConvert(usage.used, "mb"),
        "free": bytesConvert(usage.available, "mb"),
        "percent": usage.percent,
    }


def getOsInfo():
    return {
        "hostname": platform.node(),
        "platform": platform.system(),
        "arch": platform.machine(),
        "upTime": getUptime(),
    }


def bytesConvert(bytes, type):
    match type:
        case "mb":
            return round(bytes / 1024 / 1024)
        case "gb":
            return round(bytes / 1024 / 1024 / 1024)
    return round(bytes / 1048576)


def getUptime():
    with open("/proc/uptime", "r") as f:
        uptime_seconds = float(f.readline().split()[0])
        return seconds_to_dhms(round(uptime_seconds))


def seconds_to_dhms(time):
    seconds_to_minute = 60
    seconds_to_hour = 60 * seconds_to_minute
    seconds_to_day = 24 * seconds_to_hour
    days = time // seconds_to_day
    time %= seconds_to_day
    hours = time // seconds_to_hour
    time %= seconds_to_hour
    minutes = time // seconds_to_minute
    time %= seconds_to_minute
    seconds = time
    return "%d days, %d hours, %d minutes, %d seconds" % (days, hours, minutes, seconds)