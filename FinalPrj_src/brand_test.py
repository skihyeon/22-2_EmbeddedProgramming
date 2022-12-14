import os
import argparse
import cv2
import numpy as np
import sys
import time
from threading import Thread
import importlib.util
import copy
import sys

sys.path.append("/home/pi/.local/lib/python3.9/site-packages/tflite_runtime/__init__.py")

parser = argparse.ArgumentParser()
parser.add_argument('--modeldir', default = '/home/pi/Final/codes/')
parser.add_argument('--graph', default = 'detect.tflite')
parser.add_argument('--labels', default = 'labelmap.txt')
parser.add_argument('--threshold', default = 0.5)
parser.add_argument('--resolution', default = '640x480')
parser.add_argument('--edgetpu', action = 'store_true')

args = parser.parse_args()

MODEL_NAME = args.modeldir
GRAPH_NAME = args.graph
LABELMAP_NAME = args.labels
min_conf_threshold = float(args.threshold)
resW, resH = args.resolution.split('x')
imW, imH = int(resW), int(resH)
use_TPU = args.edgetpu


pkg = importlib.util.find_spec('tflite_runtime')

if pkg:
	from tflite_runtime.interpreter import Interpreter
	if use_TPU:
		from tflite_runtime.interpreter import load_delegate
else:
	from tensorflow.lite.python.interpreter import Interpreter
	if use_TPU:
		from tensorflow.lite.python.interpreter import load_delegate

if use_TPU:
	if (GRAPH_NAME == 'detect.tflite'):
		GRAPH_NAME = 'edgetpu.tflite'

CWD_PATH = os.getcwd()
PATH_TO_CKPT = os.path.join(CWD_PATH, MODEL_NAME, GRAPH_NAME)
PATH_TO_LABELS = os.path.join(CWD_PATH, MODEL_NAME, LABELMAP_NAME)

with open(PATH_TO_LABELS, 'r') as f:
	labels = [line.strip() for line in f.readlines()]

if labels[0] == '???':
	del(labels[0])

if use_TPU:
	interpreter = Interpreter(model_path = PATH_TO_CKPT, experimental_delegates = [load_delegate('libedgetpu.so.1.0')])
	print(PATH_TO_CKPT)
else:
	interpreter = Interpreter(model_path = PATH_TO_CKPT)
interpreter.allocate_tensors()


input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
height = input_details[0]['shape'][1]
width = input_details[0]['shape'][2]

floating_model = (input_details[0]['dtype'] == np.float32)

input_mean = 127.5
input_std = 127.5

outname = output_details[0]['name']

if('StatefulPartitionedCall' in outname):
	boxes_idx, classes_idx, scores_idx = 1, 3, 0
else:
	boxes_idx, classes_idx, scores_idx = 0, 1, 2

frame_rate_calc = 1
freq = cv2.getTickFrequency()


cap = cv2.VideoCapture(cv2.CAP_V4L2+0)
cap.set(3, 640)
cap.set(4, 480)

time.sleep(1)

fourcc = cv2.VideoWriter_fourcc(*'MJPG')
outVideo = cv2.VideoWriter("outVideo.avi",fourcc,10,(640,480));

while True:
	t1 = cv2.getTickCount()
	frame1 = videostream.read()

	frame = frame1.copy()
	frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
	frame_resized = cv2.resize(frame_rgb, (width, height))
	input_data = np.expand_dims(frame_resized, axis=0)

	
	mask = np.zeros((480,640), dtype = np.uint8)

	boxing_img = frame1.copy()
	blurred_img = frame1.copy()

	if floating_model:
		input_data = (np.float32(input_data)-input_mean) / input_std

	interpreter.set_tensor(input_details[0]['index'],input_data)
	interpreter.invoke()

	boxes = interpreter.get_tensor(output_details[boxes_idx]['index'])[0]
	classes = interpreter.get_tensor(output_details[classes_idx]['index'])[0]
	scores = interpreter.get_tensor(output_details[scores_idx]['index'])[0]

	for i in range(len(scores)):
		if((scores[i] > min_conf_threshold) and (scores[i] <= 1.0)):
			ymin = int(max(1, (boxes[i][0] * imH)))
			xmin = int(max(1, (boxes[i][1] * imW)))
			ymax = int(min(imH, (boxes[i][2] * imH)+5))
			xmax = int(min(imW, (boxes[i][3] * imW)+5))

			for y in range(ymin, ymax):
				for x in range(xmin, xmax):
					frame[y,x] = [255,255,255]
					mask[y,x] = 255
			blurred_img = cv2.inpaint(frame, mask, 5, cv2.INPAINT_TELEA)

			cv2.rectangle(boxing_img, (xmin,ymin), (xmax,ymax), (10,255,0), 2)


			object_name = labels[int(classes[i])]
			label = '%s: %d%%' % (object_name, int(scores[i]*100))
			labelSize, baseLine = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
			label_ymin = max(ymin, labelSize[1] + 10)
			cv2.rectangle(boxing_img, (xmin, label_ymin-labelSize[1]-10), (xmin+labelSize[0], label_ymin+baseLine-10), (255, 255, 255), cv2.FILLED)
			cv2.putText(boxing_img, label, (xmin, label_ymin-7), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

	cv2.putText(boxing_img,'FPS: {0:.2f}'.format(frame_rate_calc),(30,50),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,0),2,cv2.LINE_AA)
	cv2.putText(blurred_img,'FPS: {0:.2f}'.format(frame_rate_calc),(30,50),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,0),2,cv2.LINE_AA)

	#cv2.imshow('label img', boxing_img)
	#cv2.imshow('blurred img', blurred_img)
	#cv2.imshow('mask', mask)
	t2 = cv2.getTickCount()
	time1 = (t2-t1)/freq
	frame_rate_calc = 1/time1

	outVideo.write(blurred_img)

	if cv2.waitKey(1) == ord('q'):
		break