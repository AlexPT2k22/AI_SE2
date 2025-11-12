from fast_alpr import ALPR

alpr = ALPR(
    detector_model="yolo-v9-t-384-license-plate-end2end",
    ocr_model="cct-s-v1-global-model",
)

# The "assets/test_image.png" can be found in repo root dir
#alpr_results = alpr.predict("assets/test_image.png")
#print(alpr_results)