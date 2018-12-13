#%%
import numpy as np
import cv2

im_grasp = cv2.imread('./dataset/aff/hammer1_beige_000_grasp_0label.png')
im_pound = cv2.imread('./dataset/aff/hammer1_beige_000_pound_2label.png')
im_hand = cv2.imread('./dataset/aff/hammer1_beige_000_hand_1label.png')
im_aff = cv2.imread('./dataset/aff/hammer1_beige_000_grasp_0label.png')

#%%
green = np.array([0, 255, 0])
blue = np.array([255, 0, 0])
white = np.array([255, 255, 255])
aff = cv2.imread('./dataset/aff/hammer1_beige_000_rgb.png')
grasp = cv2.imread('./dataset/aff/hammer1_beige_000_rgb.png')
pound = cv2.imread('./dataset/aff/hammer1_beige_000_rgb.png')
hand = cv2.imread('./dataset/aff/hammer1_beige_000_rgb.png')

#%%
h, w, _ = im_pound.shape
for i in range(h):
    for j in range(w):
        if im_pound[i, j, 0] == 255 and im_pound[i, j, 1] == 0:
            im_pound[i, j] = [0, 0, 255]
        
        if im_aff[i, j, 2] == 255 and im_aff[i, j, 1] == 255 and im_aff[i, j, 0] == 255:
            im_aff[i, j] = [0, 0, 255]


a = cv2.addWeighted(grasp, 0.6, im_grasp, 0.4, 0)
b = cv2.addWeighted(pound, 0.6, im_pound, 0.4, 0)
c = cv2.addWeighted(hand, 0.6, im_hand, 0.4, 0)
d = cv2.addWeighted(aff, 0.6, im_aff, 0.4, 0)
cv2.imwrite('./dataset/aff/a.png', a)
cv2.imwrite('./dataset/aff/b.png', b)
cv2.imwrite('./dataset/aff/c.png', c)
cv2.imwrite('./dataset/aff/d.png', d)


#%%
