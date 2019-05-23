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

def validate(json_path, h5_path, data_path, mask_path=None):
    data_nii = np.load(data_path)
    mask_nii = np.load(mask_path)
    segment_number = 2000
    data_nii, mask_nii = ExtractInfo(data_nii, mask_nii)
    # model = load_model(h5_path, custom_objects={'focal_loss_fixed': focal_loss(gamma=2.0)})
    model = load_model(h5_path)
    _sum = 0
    for i in range(data_nii.shape[0]):
        # 在原图验证
        slice_ = data_nii[i, :, :]
        myslice = slice_.copy()
        label_ = mask_nii[i, :, :]
        # 寻找身体中心来定位
        # cut_slice = cutheart(img=slice_)
        # cut_label = cutheart(img=label_)
        cut_slice = slice_
        cut_label = label_
        # ShowImage(2, slice_, label_, cut_slice, cut_label)
        PatchNorm,  region, superpixel, slice_entro = SuperpixelExtract(cut_slice, segment_number, is_data_from_nii=0)
        labelvalue, patch_data, patch_coord, count, region_index, patch_liver_index = PatchExtract(region, cut_slice, cut_label)
        Patch_test, Label_test = np.array(patch_data), np.array(labelvalue)
        Patch_test = Patch_test.astype(np.float32)
        Patch_test = np.expand_dims(Patch_test, -1)

        Label_test = np_utils.to_categorical(Label_test, num_classes=3)


        # model.load_weights(r'F:\practice\try\weights-improvement-04-0.77.hdf5')
        # Evaluate the model with the metrics defined earlier
        loss, accuracy = model.evaluate(Patch_test, Label_test)
        print("loss: %g,training accuracy: %g" % (loss, accuracy))
        prediction = model.predict(Patch_test)
        prediction = np.argmax(prediction, 1)
        y_shape, x_shape = cut_slice.shape[0], cut_slice.shape[1]
        whiteboard = np.zeros((y_shape, x_shape))
        whiteboard_region = np.zeros((y_shape, x_shape))
        whiteboard_region_2 = np.zeros((y_shape, x_shape))
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
        for lindex3 in patch_liver_index:
            temp_region = region[lindex3]
            for value in temp_region.coords:
                whiteboard_region_2[value[0], value[1]] = 1
            # 膨胀腐蚀
            # TODO Step1 填补内部空洞，防止腐蚀造成原本连续的断裂
        first_fill = Fill_holes(whiteboard_region)
        # TODO Step2 腐蚀，因预测出来的心脏模型是纺锤型，期望蚀断头尾突出部
        whiteboard_region_erosion = morphology.erosion(first_fill, morphology.disk(6))

        # TODO Step3 预测结果会有多处联通区域，希望能找到最接近于心脏中心点的一块
        whiteboard_region_after_remove = measure.label(whiteboard_region_erosion, connectivity=1)
        afterregions = regionprops(whiteboard_region_after_remove)

        # 去除非中心区域的联通区域
        validate_area = wipe_out_uncenter(afterregions, 512, 512)

        # for i in range(len(afterregions)):
        #     validate_area.append(afterregions[i].area)
        if len(validate_area) > 0:
            maxlabel = max_label(validate_area)
            whiteboard_region_after_remove[whiteboard_region_after_remove != maxlabel] = 0
            whiteboard_region_after_remove[whiteboard_region_after_remove == maxlabel] = 1
            whiteboard_region_after_dilation = morphology.dilation(whiteboard_region_after_remove,
                                                                   morphology.disk(6))

            # 二值边界平滑处理
            blurbinary_rel = whiteboard_region_after_dilation.copy()
            for tag in range(10):
                blurbinary_rel = morphology.dilation(blurbinary_rel, morphology.disk(3))
                blurbinary_rel = morphology.erosion(blurbinary_rel, morphology.disk(2))
            last_finish = morphology.erosion(blurbinary_rel, morphology.disk(4))
            last_finish = morphology.erosion(last_finish, morphology.disk(3))
            # 取contours
            coords = extract_counters(last_finish)
            draw = draw_coords_img(cut_slice, coords, value=200)
            #
            ShowImage(3, slice_, whiteboard_region, first_fill, whiteboard_region_erosion,
                      whiteboard_region_after_remove, whiteboard_region_after_dilation,
                      blurbinary_rel, last_finish, draw)

            ShowImage(1, draw)
            # ShowImage(2, slice_, label_, draw)
            # dice = 2 * np.sum(cut_label*last_finish)/(np.sum(last_finish) + np.sum(cut_label))
            # _sum += dice
            # print(dice)
        else:
            print("该行无预测")
    # print('平均dice系数为：',  str(_sum / data_nii.shape[0]))
    a = 1

# 结果dice 系数有点差异
# 0.94, 0.87, 0.89, 0.77, 0.85
# 130：0.7325；125： 0.83
json_path = r'G:\model-store\heart-model\segliver_model_3cnn_50ecrossentry_2000.json'
h5_path = r'G:\model-store\heart-model\segliver_model_3cnn_50ecrossentry_2000.h5'
# json_path = r'H:\Hospital_Data\heart\masks\segliver_model_3cnn_10ecrossentry_2000.json'
# h5_path = r'H:\Hospital_Data\heart\masks\segliver_model_3cnn_10ecrossentry_2000.h5'
dcm_path = r'G:\data\heart_data\val_data\ZHENG XIANG YUN\ct_data.npy'
mask_path = r'G:\data\heart_data\val_data\ZHENG XIANG YUN\Heart.npy'
validate(json_path, h5_path, dcm_path, mask_path)
