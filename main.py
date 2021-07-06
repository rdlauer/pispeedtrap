import cv2
import os
import sys
import signal
import time
import keys
import speed
import notecard
import board
import busio
from adafruit_ht16k33 import segments
from notecard import hub, card, note, env
from periphery import I2C
from edge_impulse_linux.image import ImageImpulseRunner

# initialize variables for Edge Impulse
runner = None
dir_path = os.path.dirname(os.path.realpath(__file__))
modelfile = os.path.join(dir_path, "model.eim")

# initialize the seven-segment display
disp_i2c = busio.I2C(board.SCL, board.SDA)
display = segments.Seg7x4(disp_i2c)
display.fill(0)

# initialize the Blues Wireless Notecard (blues.io)
productUID = keys.PRODUCT_UID
port = I2C("/dev/i2c-1")
nCard = notecard.OpenI2C(port, 0, 0)

# associate Notecard with a project on Notehub.io
rsp = hub.set(nCard,
              product=productUID,
              mode="periodic",
              outbound=10,
              inbound=10)

# start GPS location tracking with the Notecard
req = {"req": "card.location.mode"}
req["mode"] = "periodic"
req["seconds"] = 600
nCard.Transaction(req)


def now():
    return round(time.time() * 1000)


def sigint_handler(sig, frame):
    print('Interrupted')
    if (runner):
        runner.stop()
    sys.exit(0)


signal.signal(signal.SIGINT, sigint_handler)


def main():
    with ImageImpulseRunner(modelfile) as runner:
        try:
            model_info = runner.init()
            print('Loaded runner for "' +
                  model_info['project']['owner'] + ' / ' + model_info['project']['name'] + '"')
            labels = model_info['model_parameters']['labels']

            videoCaptureDeviceId = 0

            camera = cv2.VideoCapture(videoCaptureDeviceId)
            ret = camera.read()[0]
            if ret:
                backendName = camera.getBackendName()
                w = camera.get(3)
                h = camera.get(4)
                print("Camera %s (%s x %s) in port %s selected." %
                      (backendName, h, w, videoCaptureDeviceId))
                camera.release()
            else:
                raise Exception("Couldn't initialize selected camera.")

            next_frame = 0  # limit to ~10 fps here

            for res, img in runner.classifier(videoCaptureDeviceId):
                if (next_frame > now()):
                    time.sleep((next_frame - now()) / 1000)

                if "classification" in res["result"].keys():
                    print('Result (%d ms.) ' % (
                        res['timing']['dsp'] + res['timing']['classification']), end='')
                    for label in labels:
                        score = res['result']['classification'][label]
                        print('%s: %.2f\t' % (label, score), end='')
                    print('', flush=True)

                elif "bounding_boxes" in res["result"].keys():
                    print('Found %d bounding boxes (%d ms.)' % (len(
                        res["result"]["bounding_boxes"]), res['timing']['dsp'] + res['timing']['classification']))
                    display.fill(0)
                    # get the speed of the object before we start any processing
                    current_speed = speed.ops_get_speed()

                    for bb in res["result"]["bounding_boxes"]:
                        # print('\t%s (%.2f): x=%d y=%d w=%d h=%d' % (bb['label'], bb['value'], bb['x'], bb['y'], bb['width'], bb['height']))
                        vehicle_type = bb["label"]
                        confidence = round(bb["value"] * 100)
                        print("what is it? " + vehicle_type +
                              " and how confident? " + str(confidence))
                        display.print(confidence)

                        if vehicle_type == "car" and confidence >= 60:

                            # we're pretty sure it's a vehicle we want to track, now let's get the speed
                            display.fill(0)
                            display.print(current_speed)

                            # get the current speed limit
                            rsp = env.get(nCard, name="speed-limit")
                            speed_limit = 0
                            print(rsp)

                            if "text" in rsp:
                                speed_limit = int(rsp["text"])

                            # get the current GPS location
                            req = {"req": "card.location"}
                            rsp = nCard.Transaction(req)
                            lat = 43.073051  # default lat for madison, wi, usa
                            lon = -89.401230  # default lon for madison, wi, usa
                            print(rsp)

                            if "lat" in rsp and "lon" in rsp:
                                lat = float(rsp["lat"])
                                lon = float(rsp["lon"])

                            # is the vehicle speeding?
                            is_speeding = 0

                            if speed_limit > 0 and current_speed >= speed_limit + 5:
                                is_speeding = 1

                            timestamp = now()

                            # add a note
                            rsp = note.add(nCard,
                                           file="speed.qo",
                                           body={
                                               "timestamp": timestamp,
                                               "confidence": confidence,
                                               "lat": lat,
                                               "lng": lon,
                                               "speed": current_speed,
                                               "speed_limit": speed_limit,
                                               "is_speeding": is_speeding
                                           })

                            print(rsp)
                            time.sleep(1)

                next_frame = now() + 100
        finally:
            if runner:
                runner.stop()


while True:
    main()
