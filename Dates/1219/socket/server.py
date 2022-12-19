import socket
import numpy
import cv2

UDP_IP='192.168.222.1'
UDP_PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

s = [b'\xff'*46080 for x in range(20)]

fourcc = cv2.VideoWriter_fourcc(*'DIVX')
out = cv2.VideoWriter('out.avi',fourcc,25,(640,480))

try:
	while True:
		pciture = b''

		data, addr = sock.recvfrom(46081)
		s[data[0]] = data[1:46081]

		if data[0] == 19:
			for i in range(20):
				picture += s[i]

		frame = numpy.fromstring(picture, dtype = numpy.uint8)
		frame = frame.reshape(480,640,3)
		cv2.imshow("frame", frame)
		out.write(frame)
except KeyboardInterrupt:
	quit()