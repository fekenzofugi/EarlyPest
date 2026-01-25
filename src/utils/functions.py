import ee
import os
import requests
import shutil
from retry import retry


def get_files_info(directory):
    os.makedirs(directory, exist_ok=True)

    file_list = os.listdir(directory)

    file_list = [file for file in file_list if os.path.isfile(os.path.join(directory, file))]

    num_files = len(file_list)

    print(f'Total number of files: {num_files}')

    img_ids = file_list 
    
    return num_files, img_ids

def getRequests(params, image, region):
    img = ee.Image(1).rename("Class").addBands(image)
    points = img.stratifiedSample(
        numPoints=params["count"],
        region=region,
        scale=params["scale"],
        seed=params["seed"],
        geometries=True,
    )
    
    return points.aggregate_array(".geo").getInfo()

@retry(tries=10, delay=1, backoff=2)
def getResult(index, point, image, params, id):
    import re

    point = ee.Geometry.Point(point["coordinates"])
    region = point.buffer(params["buffer"]).bounds()

    if params["format"] in ["png", "jpg"]:
        url = image.getThumbURL(
            {
                "region": region,
                "dimensions": params["dimensions"],
                "format": params["format"],
            }
        )
    else:
        url = image.getDownloadURL(
            {
                "region": region,
                "dimensions": params["dimensions"],
                "format": params["format"],
                "bands": params["bands"],
                "crs": params["crs"],
            }
        )

    if params["format"] == "GEO_TIFF":
        ext = "tif"
    else:
        ext = params["format"]

    date_match = re.search(r"_(\d{8})T", id)
    if date_match:
        date_prefix = date_match.group(1)
    else:
        date_match = re.search(r"_(\d{8})_\d{8}_\d{2}_T\d", id)
        if date_match:
            date_prefix = date_match.group(1)
        else:
            date_prefix = "unknown_date"

    out_dir = os.path.abspath(params["out_dir"])
    basename = str(index).zfill(len(str(params["count"])))
    filename = f"{out_dir}/{date_prefix}_{id}_{params['prefix']}{basename}.{ext}"

    r = requests.get(url, stream=True)
    if r.status_code != 200:
        r.raise_for_status()

    with open(filename, "wb") as out_file:
        shutil.copyfileobj(r.raw, out_file)

    print("Download Completed:", filename)
