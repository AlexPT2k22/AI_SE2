from roboflow import Roboflow

rf = Roboflow(api_key="RglxtAlqg9vzbsgaxq1q")
project = rf.workspace().project("car-space-find")
model = project.version(2).model
# Roboflow only accepts format strings such as "pt" or "yolov8".
model.download("pt")
