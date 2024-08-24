from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import psutil
import platform
from slowapi import Limiter, _rate_limit_exceeded_handler
import time

from slowapi.errors import RateLimitExceeded

def get_real_ipaddr(request: Request) -> str:
    if "cf-connecting-ip" in request.headers:
        return request.headers["cf-connecting-ip"]
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"]
    else:
        if not request.client or not request.client.host:
            return "127.0.0.1"
        return request.client.host

limiter = Limiter(key_func=get_real_ipaddr)

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
@limiter.limit("2/second")
async def getStats(request: Request):
    return {
        "cpuTemp": getCpuTemp(),
        "cpuPercent": getCpuPercent(),
        "diskUsage": getAllDiskUsage(),
        "memUsage": getMemoryUsage(),
        "os": getOsInfo(),
        "network": getNetwork()
    }

@app.get("/test")
@limiter.limit("2/second")
async def getStats(request: Request):
    net_usage()

def getCpuTemp():
    return psutil.sensors_temperatures().get("cpu_thermal")[0].current


def getCpuPercent():
    return psutil.cpu_percent(percpu=True)

def getAllDiskUsage():
    rootUsage = getDiskUsage('/')
    mediaUsage = getDiskUsage('/media/fatboy')
    return [
        rootUsage,
        mediaUsage
    ]

def getDiskUsage(path):
    usage = psutil.disk_usage(path)
    return {
        "name": 'fatboy' if path =='/media/fatboy' else 'root',
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
    
def getNetwork():
    inMb, outMb, totalIn, totalOut = net_usage()
    return {
        "inSpeed": inMb,
        "outSpeed": outMb,
        "totalIn": totalIn,
        "totalOut": totalOut
    }
    
def net_usage(inf = "eth0"): 
    net_stat = psutil.net_io_counters(pernic=True, nowrap=True)[inf]
    net_in_1 = net_stat.bytes_recv
    net_out_1 = net_stat.bytes_sent
    time.sleep(1)
    net_stat = psutil.net_io_counters(pernic=True, nowrap=True)[inf]
    net_in_2 = net_stat.bytes_recv
    net_out_2 = net_stat.bytes_sent

    net_in = round((net_in_2 - net_in_1) / 1024 / 1024, 3)
    net_out = round((net_out_2 - net_out_1) / 1024 / 1024, 3)

    return net_in, net_out, round(net_in_2 / 1024 / 1024), round(net_out_2 / 1024 / 1024)
    

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