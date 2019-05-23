from core.shelper import *
import numpy as np
from keras.utils import np_utils
from keras.models import Sequential
from keras.layers import Dense,Activation,Convolution2D,MaxPooling2D,Flatten
from keras.optimizers import Adam
from keras.models import load_model
from model_3cnn_focalloss import focal_loss
from skimage import morphology, measure
from skimage.measure import regionprops
import cv2

def predict(json_path, h5_path, data):
    data_nii = data
    segment_number = 2000
    model = load_model(h5_path)
    _sum = 0
    for i in range(data_nii.shape[0]):
        # 在原图验证
        slice_ = data_nii[i, :, :]
        cut_slice = cutheart(img=slice_)
        PatchNorm,  region, superpixel, slice_entro = SuperpixelExtract(cut_slice, segment_number, is_data_from_nii=1)
        patch_data, patch_coord, region_index = PatchExtract_for_eval(region, cut_slice)
        Patch_test = np.array(patch_data)
        Patch_test = Patch_test.astype(np.float32)
        Patch_test = np.expand_dims(Patch_test, -1)

        prediction = model.predict(Patch_test)
        prediction = np.argmax(prediction, 1)
        y_shape, x_shape = cut_slice.shape[0], cut_slice.shape[1]
        whiteboard = np.zeros((y_shape, x_shape))
        whiteboard_region = np.zeros((y_shape, x_shape))
        liver_index = []

        for index, value in enumerate(prediction):
            if value == 1:
                liver_index.append(index)
            if value == 2:
                liver_index.append(index)
        for lindex in liver_index:
            coord = patch_coord[lindex]
            whiteboard[coord[0]: coord[1], coord[2]: coord[3]] = 1
        for lindex2 in liver_index:
            temp_region = region[region_index[lindex2]]
            for value in temp_region.coords:
                whiteboard_region[value[0], value[1]] = 1
        # 膨胀腐蚀
        whiteboard_region_after = morphology.dilation(whiteboard_region, morphology.disk(5))
        whiteboard_region_after = morphology.erosion(whiteboard_region_after, morphology.disk(5))
        whiteboard_region_after_remove = measure.label(whiteboard_region_after, connectivity=2)
        afterregions = regionprops(whiteboard_region_after_remove)

        validate_area = []

        for i in range(len(afterregions)):
            validate_area.append(afterregions[i].area)
        if len(validate_area) > 0:
            # 去除外围最小联通区域
            whiteboard_region_after_remove[whiteboard_region_after_remove != validate_area.index(max(validate_area)) + 1] = 0
            whiteboard_region_after_remove[whiteboard_region_after_remove == validate_area.index(max(validate_area)) + 1] = 1
            # 泛洪算法fill hole
            FillHolesFinish = Fill_holes(whiteboard_region_after_remove)

            # 二值边界平滑处理
            blurbinary_rel = FillHolesFinish.copy()
            for tag in range(10):
                blurbinary_rel = morphology.dilation(blurbinary_rel, morphology.disk(3))
                blurbinary_rel = morphology.erosion(blurbinary_rel, morphology.disk(2))
            last_finish = morphology.erosion(blurbinary_rel, morphology.disk(4))
            last_finish = morphology.erosion(last_finish, morphology.disk(3))
            # 取contours
            # coords = find_counters_by(last_finish, 1)
            coords = extract_counters(last_finish)
            draw = draw_coords_img(cut_slice, coords, value=200)

            ShowImage(3, slice_, whiteboard_region,  whiteboard_region_after,
                      whiteboard_region_after_remove, FillHolesFinish, blurbinary_rel, last_finish, draw)
            ShowImage(1, draw)
            # ShowImage(2, slice_, label_, draw)
            # dice = 2 * np.sum(cut_label*last_finish)/(np.sum(last_finish) + np.sum(cut_label))
            # _sum += dice
            # print(dice)
        else:
            print("该行无预测")
    # print('平均dice系数为：',  str(_sum / data_nii.shape[0]))
    a = 1

json_path = r'G:\model-store\heart-model\segliver_model_3cnn_50ecrossentry_2000.json'
h5_path = r'G:\model-store\heart-model\segliver_model_3cnn_50ecrossentry_2000.h5'
# json_path = r'H:\Hospital_Data\heart\masks\segliver_model_3cnn_10ecrossentry_2000.json'
# h5_path = r'H:\Hospital_Data\heart\masks\segliver_model_3cnn_10ecrossentry_2000.h5'
dcm_path = r'G:\data\heart_data\heart_masks\20190313_heart_masks\val_mask\ZHANG GUO LIANG\ct_data.npy'
mask_path = r'G:\data\heart_data\heart_masks\20190313_heart_masks\val_mask\ZHANG GUO LIANG\Heart.npy'
predict(json_path, h5_path, dcm_path, mask_path)
