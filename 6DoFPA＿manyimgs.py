# 6DoF pose annotator 
# Shuichi Akizuki, Keio Univ.
# Email: akizuki@elec.keio.ac.jp

""" annotate all images with a single 3D model """

import open3d as o3 
import numpy as np
import cv2
import copy
import argparse
import os
import common3Dfunc as c3D
import glob
from math import *

""" Object model to be transformed """
CLOUD_ROT = o3.PointCloud()
""" Total transformation"""
all_transformation = np.identity(4)
""" Step size for rotation """
step = 0.1*pi
""" Voxel size for downsampling"""
voxel_size = 0.005

def get_argumets():
    """
        Parse arguments from command line
    """

    parser = argparse.ArgumentParser( description='Interactive 6DoF pose annotator')
    parser.add_argument('--img_folder', type=str, default='./img',
                        help='the folder name where RGB images and depth images of the input scene are saved.')
    parser.add_argument('--intrin', type=str, default='data/realsense_intrinsic.json',
                        help='file name of the camera intrinsic.')
    parser.add_argument('--model', type=str, default='dataset/hammer_1_grasp.pcd',
                        help='file name of the object models(.pcd or .ply).')
    parser.add_argument('--task_num', type=str, default='0',
                        help='task name.(choose grasp: 0/hand: 1/pound: 2)')       
    parser.add_argument('--init', type=str, default='data/init.json',
                        help='file name of the initial transformation (.json).')
    
    return parser.parse_args()

class Mapping():
    def __init__(self, camera_intrinsic_name, _w=640, _h=480, _d=1000.0 ):
        self.camera_intrinsic = o3.read_pinhole_camera_intrinsic(camera_intrinsic_name)
        self.width = _w
        self.height = _h
        self.d = _d
        self.camera_intrinsic4x4 = np.identity(4)
        self.camera_intrinsic4x4[0,0] = self.camera_intrinsic.intrinsic_matrix[0,0]
        self.camera_intrinsic4x4[1,1] = self.camera_intrinsic.intrinsic_matrix[1,1]
        self.camera_intrinsic4x4[0,3] = self.camera_intrinsic.intrinsic_matrix[0,2]
        self.camera_intrinsic4x4[1,3] = self.camera_intrinsic.intrinsic_matrix[1,2]
        
    def showCameraIntrinsic(self):
        print(self.camera_intrinsic.intrinsic_matrix)
        print(self.camera_intrinsic4x4)

    def Cloud2Image( self, cloud_in ):
        
        img = np.zeros( [self.height, self.width], dtype=np.uint8 )
        
        cloud_np = np.asarray(cloud_in.points)
        cloud_np = cloud_np[:,:] / cloud_np[:,[2]]

        cloud_min = np.min(cloud_np,axis=0)

        cloud_mapped = o3.PointCloud()
        cloud_mapped.points = o3.Vector3dVector(cloud_np)
        cloud_mapped.transform(self.camera_intrinsic4x4)
        cloud_color = np.asarray(cloud_in.colors)

        """ If cloud_in has the field of color, color is mapped into the image. """
        if len(cloud_color) == len(cloud_np):
            img = cv2.merge((img,img,img))
            for i, pix in enumerate(cloud_mapped.points):
                if pix[0]<self.width and 0<pix[0] and pix[1]<self.height and 0<pix[1]:
                    img[int(pix[1]),int(pix[0])] = (cloud_color[i]*255.0).astype(np.uint8)

        
        else:
            for i, pix in enumerate(cloud_mapped.points):
                if pix[0]<self.width and 0<pix[0] and pix[1]<self.height and 0<pix[1]:
                    img[int(pix[1]),int(pix[0])] = int(255.0*(cloud_np[i,2]/cloud_min[2]))

            img = cv2.merge((img,img,img))
        
        return img
    
    def Pix2Pnt( self, pix, val ):
        pnt = np.array([0.0,0.0,0.0], dtype=np.float)
        depth = val / self.d
        #print('[0,2]: {}'.format(self.camera_intrinsic.intrinsic_matrix[0,2]))
        #print('[1,2]: {}'.format(self.camera_intrinsic.intrinsic_matrix[1,2]))
        #print(self.camera_intrinsic.intrinsic_matrix)
        pnt[0] = (float(pix[0]) - self.camera_intrinsic.intrinsic_matrix[0,2]) * depth / self.camera_intrinsic.intrinsic_matrix[0,0]
        pnt[1] = (float(pix[1]) - self.camera_intrinsic.intrinsic_matrix[1,2]) * depth / self.camera_intrinsic.intrinsic_matrix[1,1]
        pnt[2] = depth

        return pnt


def mouse_event(event, x, y, flags, param):
    w_name, img_c, img_d, mapping = param

    """Direct move. Object model will be moved to clicked position."""
    if event == cv2.EVENT_LBUTTONUP:
        global all_transformation
        print('Clicked({},{}): depth:{}'.format(x, y, img_d[y,x]))
        print(img_d[y,x])
        pnt = mapping.Pix2Pnt( [x,y], img_d[y,x] )
        print('3D position is', pnt)

        #compute current center of the cloud
        cloud_c = copy.deepcopy(CLOUD_ROT)
        cloud_c, center = c3D.Centering(cloud_c)
        np_cloud = np.asarray(cloud_c.points) 

        np_cloud += pnt
        print('Offset:', pnt )
        offset = np.identity(4)
        offset[0:3,3] -= center
        offset[0:3,3] += pnt
        all_transformation = np.dot( offset, all_transformation )

        CLOUD_ROT.points = o3.Vector3dVector(np_cloud)
        generateImage( mapping, img_c )

# Pose refinement by ICP
def refine_registration(source, target, trans, voxel_size):
    global all_transformation
    distance_threshold = voxel_size * 0.4
    print(":: Point-to-point ICP registration is applied on original point")
    print("   clouds to refine the alignment. This time we use a strict")
    print("   distance threshold %.3f." % distance_threshold)
    result = o3.registration_icp(source, target, 
            distance_threshold, trans,
            o3.TransformationEstimationPointToPoint())

    return result.transformation

def generateImage( mapping, im_color ):
    global CLOUD_ROT

    img_m = mapping.Cloud2Image( CLOUD_ROT )
    img_mapped = cv2.addWeighted(img_m, 0.5, im_color, 0.5, 0 )
    cv2.imshow( window_name, img_mapped )

if __name__ == "__main__":

    args = get_argumets()

    green = np.array([0, 255, 0])
    red = np.array([0, 0, 255])
    white = np.array([255, 255, 255])
        
    img_list = glob.glob(args.img_folder + '/*rgb.png')
    img_list.sort()

    for  i, cimg in enumerate(img_list):
        """Data loading"""
        print(":: Load two point clouds to be matched.")
        color_raw = o3.read_image( cimg )

        dimg = cimg[:-7] + 'depth.png'
        depth_raw = o3.read_image( dimg )
        camera_intrinsic = o3.read_pinhole_camera_intrinsic( args.intrin )

        im_color = np.asarray(color_raw)
        im_color = cv2.cvtColor( im_color, cv2.COLOR_BGR2RGB )
        im_depth = np.asarray(depth_raw)

        rgbd_image = o3.create_rgbd_image_from_color_and_depth( color_raw, depth_raw, 1000.0, 2.0 )
        pcd = o3.create_point_cloud_from_rgbd_image(rgbd_image, camera_intrinsic )
        o3.write_point_cloud( "cloud_in.ply", pcd )
        cloud_in_ds = o3.voxel_down_sample(pcd, 0.005)
        o3.write_point_cloud( "cloud_in_ds.ply", cloud_in_ds )

        np_pcd = np.asarray(pcd.points)

        """Loading of the object model"""
        print('Loading: {}'.format(args.model))
        cloud_m = o3.read_point_cloud( args.model )
        """ if you use object model with meter scale, try this code to convert meter scale."""
        #cloud_m = c3D.Scaling( cloud_m, 0.001 )

        cloud_m_ds = o3.voxel_down_sample( cloud_m, voxel_size )

        """Loading of the initial transformation"""
        initial_trans = np.identity(4)
        if i ==0:
            if os.path.exists( args.init ):
                initial_trans = c3D.load_transformation( args.init )
                print('Use initial transformation\n', initial_trans )
                all_transformation = np.dot( initial_trans, all_transformation )
            else:
                # if initial transformation is not avairable, 
                # the object model is moved to its center.
                cloud_m_c, offset = c3D.Centering( cloud_m_ds )
                mat_centering = c3D.makeTranslation4x4( -1.0*offset )
                all_transformation = np.dot( mat_centering, all_transformation )
        else:
            pass

        CLOUD_ROT = copy.deepcopy(cloud_m_ds)
        CLOUD_ROT.transform( all_transformation )

        mapping = Mapping('./data/realsense_intrinsic.json')
        img_mapped = mapping.Cloud2Image( CLOUD_ROT )

        """Mouse event"""
        window_name = '6DoF Pose Annotator'
        cv2.namedWindow( window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback( window_name, mouse_event, 
                            [window_name, im_color, im_depth, mapping])

        generateImage( mapping, im_color )
        while (True):
            key = cv2.waitKey(1) & 0xFF
            """Quit"""
            if key == ord("q"):
                break
            """ICP registration"""
            if key == ord("i"):
                print('ICP start (coarse mode)')
                result_icp = refine_registration( CLOUD_ROT, pcd, np.identity(4), 10.0*voxel_size)
                CLOUD_ROT.transform( result_icp )
                all_transformation = np.dot( result_icp, all_transformation )

                generateImage( mapping, im_color )

            if key == ord("f"):
                print('ICP start (fine mode)')
                result_icp = refine_registration( CLOUD_ROT, pcd, np.identity(4), 3.0*voxel_size)
                CLOUD_ROT.transform( result_icp )
                all_transformation = np.dot( result_icp, all_transformation )
                generateImage( mapping, im_color )


            """Step rotation"""
            if key == ord("1"):
                print('Rotation around roll axis')
                rotation = c3D.ComputeTransformationMatrixAroundCentroid( CLOUD_ROT, step, 0, 0 )
                CLOUD_ROT.transform( rotation )
                all_transformation = np.dot( rotation, all_transformation )

                generateImage( mapping, im_color )
                
            if key == ord("2"):
                print('Rotation around pitch axis')
                rotation = c3D.ComputeTransformationMatrixAroundCentroid( CLOUD_ROT, 0, step, 0 )
                CLOUD_ROT.transform( rotation )
                all_transformation = np.dot( rotation, all_transformation )

                generateImage( mapping, im_color )
                
            if key == ord("3"):
                print('Rotation around yaw axis')
                rotation = c3D.ComputeTransformationMatrixAroundCentroid( CLOUD_ROT, 0, 0, step )
                CLOUD_ROT.transform( rotation )
                all_transformation = np.dot( rotation, all_transformation )

                generateImage( mapping, im_color )
                

        # cv2.destroyAllWindows()

        
        """ Save output files """
        # o3.write_point_cloud( "cloud_rot_ds.ply", CLOUD_ROT )
        
        cloud_m.transform( all_transformation )
        im_label = mapping.Cloud2Image( cloud_m )
        cv2.imwrite( cimg[:-7] + '_' + args.task_num + "label.png", im_label ) 
        # o3.write_point_cloud( "cloud_rot.ply", cloud_m )

        ''' save label.png as numpy npy
        black: 0    background
        green: 1    to be grasped
        red:   2    to be interacted w/ others
        white: 3    others
        BGR
        '''
        label = np.zeros((480, 640), dtype=np.uint8)
        label[np.logical_and.reduce(im_label == green, axis=2)] = 1
        label[np.logical_and.reduce(im_label == red, axis=2)] = 2
        label[np.logical_and.reduce(im_label == white, axis=2)] = 3
        # grasp: 0, hand:1, pound:2
        np.save(cimg[:-7] + '_' + args.task_num + '.npy', label, np.uint8)


        # print("\n\nFinal transformation is\n", all_transformation)
        # print("You can transform the original model to the final pose by multiplying above matrix.")
        # c3D.save_transformation( all_transformation, 'trans.json')
    

    cv2.destroyAllWindows()


