# -*- coding: utf-8 -*-
import logging
from OpenGL.GL import *
from OpenGL.GLU import *

import math

import numpy
import time


from PyQt4.QtGui import QColor
from PyQt4.QtOpenGL import *
from PyQt4 import QtCore

from PIL.Image import *

import controller
from glButton import GlButton

#Mesure
def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        logging.debug('%s function took %0.3f ms' % (f.func_name, (time2-time1)*1000.0))
        return ret
    return wrap


class GLWidget(QGLWidget):
    def __init__(self, parent=None):
        QGLWidget.__init__(self, parent)
        #TODO:Add camera instance
        self.parent = parent
        self.init_parametres()





        #properties definition
        self.xRot = 0
        self.yRot = 0
        self.zRot = 0
        self.zoom = 0

        self.oldPos3d = [.0, .0, .0]

        self.lightAmbient = [.0, .0, .0, .0]
        self.lightDiffuse = [.0, .0, .0, .0]
        self.lightPossition = [.0, .0, .0, .0]

        self.materialSpecular = [.0,.0,.0,.0]
        self.materialShiness = [.0]

        #screen properties
        self.w = 0
        self.h = 0

        self.init_parametres()

        self.sceneFrameBuffer = []
        self.image_background = []
        self.image_hotbed = []

        #tools
        self.selectTool = None
        self.moveTool = None
        self.rotateTool = None
        self.scaleTool = None
        self.tool_background = None

    def init_parametres(self):
        #TODO:Add camera instance initialization
        #properties initialization
        self.xRot = 424
        self.yRot = 0
        self.zRot = 5576
        self.zoom = -39

        self.oldPos3d = [.0, .0, .0]

        self.lightAmbient = [.95, .95, .95, 1.0]
        self.lightDiffuse = [.5, .5, .5, 1.0]
        self.lightPossition = [29.0, -48.0, 37.0, 1.0]

        self.materialSpecular = [.1, .1, .1, .1]
        self.materialShiness = [0.01]

        #screen properties
        self.w = 0
        self.h = 0

        self.sceneFrameBuffer = []

    def update_scene(self, reset=False):
        if reset:
            self.init_parametres()
        self.updateGL()

    #TODO:All this function will be changed to controll camera instance
    def set_zoom(self, diff):
        self.zoom += diff

    def get_zoom(self):
        return self.zoom

    def get_x_rotation(self):
        return self.xRot

    def get_y_rotation(self):
        return self.yRot

    def get_z_rotation(self):
        return self.zRot

    def minimumSizeHint(self):
        return QtCore.QSize(50, 50)

    def sizeHint(self):
        return QtCore.QSize(600, 480)

    def set_x_rotation(self, angle):
        angle = self.normalize_angle(angle)
        if angle != self.xRot:
            self.xRot = angle
            self.emit(QtCore.SIGNAL("xRotationChanged(int)"), angle)
            self.updateGL()

    def set_y_rotation(self, angle):
        angle = self.normalize_angle(angle)
        if angle != self.yRot:
            self.yRot = angle
            self.emit(QtCore.SIGNAL("yRotationChanged(int)"), angle)
            self.updateGL()

    def set_z_rotation(self, angle):
        angle = self.normalize_angle(angle)
        if angle != self.zRot:
            self.zRot = angle
            self.emit(QtCore.SIGNAL("zRotationChanged(int)"), angle)
            self.updateGL()

    def texture_from_png(self, filename):
        mode_to_bpp = {'1':1, 'L':8, 'P':8, 'RGB':24, 'RGBA':32, 'CMYK':32, 'YCbCr':24, 'I':32, 'F':32}

        img = open(filename)
        img = img.transpose(FLIP_TOP_BOTTOM)
        bpp = mode_to_bpp[img.mode]
        if bpp == 32:
            type = GL_RGBA
        else:
            type = GL_RGB
        img_data = numpy.array(list(img.getdata()), numpy.uint8)

        texture = glGenTextures(1)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glBindTexture(GL_TEXTURE_2D, texture)

        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, type, img.size[0], img.size[1], 0, type, GL_UNSIGNED_BYTE, img_data)
        return texture

    def initializeGL(self):
        #load textures
        self.image_background = self.texture_from_png("data/img/background.png")

        #tools
        #self.selectTool = GlButton(self.texture_from_png("gui/select_n.png"), [4.,4.], [95, 16])
        self.moveTool = GlButton(self.texture_from_png("data/img/move_n.png"), [4.,4.], [95,11])
        self.rotateTool = GlButton(self.texture_from_png("data/img/rotate_n.png"), [4.,4.], [95,6])
        self.scaleTool = GlButton(self.texture_from_png("data/img/scale_n.png"), [4.,4.], [95,1])

        #self.selectTool.set_callback(self.parent.controller.selectButtonPressed)
        self.moveTool.set_callback(self.parent.controller.move_button_pressed)
        self.rotateTool.set_callback(self.parent.controller.rotate_button_pressed)
        self.scaleTool.set_callback(self.parent.controller.scale_button_pressed)

        self.tool_background = self.texture_from_png("data/img/tool_background.png")

        self.bed = {}
        for i in self.parent.controller.printers:
            self.bed[i['name']] = self.makePrintingBed(i['texture'], i['printing_space'])

        #self.axis = self.make_axis()

        glClearDepth(1.0)
        glShadeModel(GL_FLAT)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glCullFace(GL_BACK)

        glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)

        glAlphaFunc( GL_GREATER, 0. )
        glEnable( GL_ALPHA_TEST )

        #new light settings
        glLightfv(GL_LIGHT0, GL_POSITION, _gl_vector(50, 50, 100, 0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, _gl_vector(.5, .5, 1, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, _gl_vector(1, 1, 1, 1))
        glLightfv(GL_LIGHT1, GL_POSITION, _gl_vector(100, 0, 50, 0))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, _gl_vector(.5, .5, .5, 1))
        glLightfv(GL_LIGHT1, GL_SPECULAR, _gl_vector(1, 1, 1, 1))
        #new light settings

        #new material settings
        #glMaterialfv(GL_FRONT, GL_AMBIENT, _gl_vector(0.192250, 0.192250, 0.192250))
        #glMaterialfv(GL_FRONT, GL_DIFFUSE, _gl_vector(0.507540, 0.507540, 0.507540))
        #glMaterialfv(GL_FRONT, GL_SPECULAR, _gl_vector(.5082730,.5082730,.5082730))
        #glMaterialf(GL_FRONT, GL_SHININESS, .4 * 128.0);
        #new material settings


        #material
        glMaterialfv(GL_FRONT, GL_SPECULAR, self.materialSpecular)
        glMaterialfv(GL_FRONT, GL_SHININESS, self.materialShiness)

        #light
        #glLightfv(GL_LIGHT0, GL_AMBIENT, self.lightAmbient)
        #glLightfv(GL_LIGHT0, GL_DIFFUSE, self.lightDiffuse)
        #glLightfv(GL_LIGHT0, GL_POSITION, self.lightPossition)
        #glEnable(GL_LIGHT0)


        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glEnable(GL_COLOR_MATERIAL)
        #glColorMaterial ( GL_FRONT_AND_BACK, GL_EMISSION )
        #glColorMaterial ( GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE )
        glBlendFunc(GL_SRC_ALPHA,GL_ONE)

        #glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_MULTISAMPLE)
        glEnable(GL_LINE_SMOOTH)
        #glEnable( GL_BLEND )
        glEnable( GL_LIGHT0 )
        glEnable( GL_LIGHT1 )

    #@timing
    def paintGL(self, selection = 1):
        #print('Coords: ' + str(self.xRot) + ' ' + str(self.yRot) + ' ' + str(self.zRot) + ' ' + str(self.zoom))
        if selection:
            glClearColor(0.0, 0.0, 0.0, 1.0)
            #glClearColor(1.0, 1.0, 1.0, 1.0)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glLoadIdentity()

            glTranslatef(0,-5,0)
            glTranslatef(0.0, 0.0, self.zoom)
            glRotated(-90.0, 1.0, 0.0, 0.0)
            glRotated(self.xRot / 16.0, 1.0, 0.0, 0.0)
            glRotated(self.zRot / 16.0, 0.0, 0.0, 1.0)
            #glLightfv(GL_LIGHT0, GL_POSITION, self.lightPossition)
            #glLightfv(GL_LIGHT1, GL_POSITION, self.lightPossition)
            glDisable( GL_LIGHTING )
            #glDisable( GL_LIGHT0 )
            glDisable( GL_BLEND )
            glEnable(GL_DEPTH_TEST)

            if self.parent.controller.scene.models:
                for model in self.parent.controller.scene.models:
                    self.draw_tools_helper(model, self.parent.controller.settings, True)
                    model.render(picking=True, debug=False)

            self.draw_tools(picking=True)

            self.sceneFrameBuffer = self.grabFrameBuffer()

            if 'debug' in self.parent.controller.settings:
                if self.parent.controller.settings['debug']:
                    self.sceneFrameBuffer.save("select_buffer.png")

            glEnable( GL_LIGHTING )

        glClearColor(0.0, 0.47, 0.62, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.draw_background_texture()
        glLoadIdentity()

        glTranslatef(0,-5,0)
        glTranslatef(0.0, 0.0, self.zoom)
        glRotated(-90.0, 1.0, 0.0, 0.0)
        glRotated(self.xRot / 16.0, 1.0, 0.0, 0.0)
        glRotated(self.zRot / 16.0, 0.0, 0.0, 1.0)
        #glLightfv(GL_LIGHT0, GL_POSITION, self.lightPossition)
        #glLightfv(GL_LIGHT1, GL_POSITION, self.lightPossition)

        glEnable( GL_BLEND )
        glCallList(self.bed[self.parent.controller.settings['printer']])
        glDisable( GL_BLEND )

        #light
        glPointSize(5)
        glColor3f(0,1,1)
        glBegin(GL_POINTS)
        glVertex3fv(self.lightPossition[:3])
        glEnd()
        glEnable(GL_DEPTH_TEST)

        if 'debug' in self.parent.controller.settings:
            if self.parent.controller.settings['debug']:
                glBegin(GL_POINTS)
                glColor3f(1,0,0)
                glVertex3fv(self.parent.controller.scene.sceneZero)
                glEnd()

                glLineWidth(5)
                glBegin(GL_LINES)
                glColor3f(0,1,0)
                glVertex3fv(self.parent.controller.ray_start)
                glVertex3fv(self.parent.controller.ray_end)
                glEnd()

        '''
        draw scene with all objects
        '''
        glDisable( GL_BLEND )
        glEnable ( GL_LIGHTING )
        if self.parent.controller.scene.models:
            for model in self.parent.controller.scene.models:
                self.draw_tools_helper(model, self.parent.controller.settings)
                model.render(picking=False, debug=self.parent.controller.settings['debug'] or False)

        glDisable( GL_LIGHTING )
        glEnable( GL_BLEND )

        self.draw_tools()

        #glFlush()

    def draw_tools_helper(self, model, settings, picking=False):
        if picking:
            rotateColors = [model.rotateColorXId, model.rotateColorYId, model.rotateColorZId]
            scaleColors = [model.scaleColorXId, model.scaleColorYId, model.scaleColorZId, model.scaleColorXYZId]
        else:
            rotateColors = [[255,0,0],[0,255,0],[0,0,255]]
            scaleColors = [[255,0,0],[0,255,0],[0,0,255], [255,255,255]]

        if settings['toolButtons']['rotateButton']:
            self.draw_rotation_circles(rotateColors, [i+o for i,o in zip(model.boundingSphereCenter, model.pos)], model.boundingSphereSize+0.1)
        #elif settings['toolButtons']['scaleButton']:
        #    self.draw_scale_axes(scaleColors, [i+o for i,o in zip(model.boundingSphereCenter, model.pos)], model.boundingSphereSize+0.1)

    def draw_rotation_circles(self, colors, position, radius, picking=False):
        segments = 24
        glPushMatrix()
        glTranslatef(position[0], position[1], position[2])
        glColor3ubv(colors[0])
        glBegin(GL_LINE_LOOP)
        for i in xrange(0, 360, 360/segments):
            glVertex3f(math.cos(math.radians(i)) * radius, math.sin(math.radians(i)) * radius, 0.0)
        glEnd()
        glColor3ubv(colors[1])
        glBegin(GL_LINE_LOOP)
        for i in xrange(0, 360, 360/segments):
            glVertex3f(0., math.cos(math.radians(i)) * radius, math.sin(math.radians(i)) * radius)
        glEnd()
        glColor3ubv(colors[2])
        glBegin(GL_LINE_LOOP)
        for i in xrange(0, 360, 360/segments):
            glVertex3f(math.cos(math.radians(i)) * radius, 0., math.sin(math.radians(i)) * radius)
        glEnd()
        glPopMatrix()

    def draw_scale_axes(self, colors, position, radius, picking=False):
        glPushMatrix()
        glTranslatef(position[0], position[1], position[2])
        glColor3ubv(colors[0])
        glBegin(GL_LINES)
        glVertex3f(0., 0., 0.)
        glVertex3f(1.*radius, 0., 0.)
        glEnd()
        glColor3ubv(colors[1])
        glBegin(GL_LINES)
        glVertex3f(0., 0., 0.)
        glVertex3f(0., 1.*radius, 0.)
        glEnd()
        glColor3ubv(colors[2])
        glBegin(GL_LINES)
        glVertex3f(0., 0., 0.)
        glVertex3f(0., 0., 1.*radius)
        glEnd()
        glColor3ubv(colors[3])
        glBegin(GL_LINES)
        glVertex3f(0., 0., 0.)
        glVertex3f(1.*radius, 1.*radius, 1.*radius)
        glEnd()
        glPopMatrix()

    def resizeGL(self, width, height):
        self.w = width
        self.h = height
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, float(width*1./height*1.), 1, 1000)
        glMatrixMode(GL_MODELVIEW)

    def mousePressEvent(self, event):
        self.parent.controller.mouse_press_event(event)

    def mouseReleaseEvent(self, event):
        self.parent.controller.mouse_release_event(event)

    def mouseMoveEvent(self, event):
        self.parent.controller.mouse_move_event(event)

    def wheelEvent(self, event):
        logging.info('MouseWheel')
        self.parent.controller.wheel_event(event)

    def get_cursor_position(self, event):
        matModelView = glGetDoublev(GL_MODELVIEW_MATRIX )
        matProjection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv( GL_VIEWPORT )

        winX = event.x() * 1.0
        winY = viewport[3] - (event.y() *1.0)

        rayStart = gluUnProject(winX, winY, 0.0, matModelView, matProjection, viewport)
        rayEnd = gluUnProject(winX, winY, 1.0, matModelView, matProjection, viewport)

        return (rayStart, rayEnd)

    def get_cursor_pixel_color(self, event):
        color = []
        winX = event.x()
        winY = event.y()
        c = QColor(self.sceneFrameBuffer.pixel(winX, winY))
        color = [c.red(), c.green(), c.blue()]
        return color

    def makePrintingBed(self, bed_texture, printing_space):
        image_hotbed = self.texture_from_png(bed_texture)

        genList = glGenLists(1)
        glNewList(genList, GL_COMPILE)

        glLineWidth(2)

        glEnable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)
        glBindTexture(GL_TEXTURE_2D, image_hotbed)

        glColor3f(1,1,1)
        glBegin(GL_QUADS)
        glNormal3f(.0,.0,1.)
        glTexCoord2f(0, 1)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*0.5, 0)

        glTexCoord2f(0, 0)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, 0)

        glTexCoord2f(1, 0)
        glVertex3d(printing_space[0]*0.5, printing_space[1]*-0.5, 0)

        glTexCoord2f(1, 1)
        glVertex3d(printing_space[0]*0.5, printing_space[1]*0.5, 0)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBegin(GL_LINES)
        glColor3f(1,1,1)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*0.5, 0)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*0.5, printing_space[2])

        glVertex3d(printing_space[0]*0.5, printing_space[1]*0.5, 0)
        glVertex3d(printing_space[0]*0.5, printing_space[1]*0.5, printing_space[2])

        glVertex3d(printing_space[0]*0.5, printing_space[1]*-0.5, 0)
        glVertex3d(printing_space[0]*0.5, printing_space[1]*-0.5, printing_space[2])

        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, 0)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, printing_space[2])
        glEnd()

        glBegin(GL_LINE_LOOP)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*0.5, printing_space[2])
        glVertex3d(printing_space[0]*0.5, printing_space[1]*0.5, printing_space[2])
        glVertex3d(printing_space[0]*0.5, printing_space[1]*-0.5, printing_space[2])
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, printing_space[2])
        glEnd()

        #Axis
        glLineWidth(5)
        glDisable(GL_DEPTH_TEST)
        glBegin(GL_LINES)
        glColor3f(1, 0, 0)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, 0)
        glVertex3d((printing_space[0]*-0.5)-1, printing_space[1]*-0.5, 0)

        glColor3f(0, 1, 0)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, 0)
        glVertex3d(printing_space[0]*-0.5, (printing_space[1]*-0.5)-1, 0)

        glColor3f(0, 0, 1)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, 0)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, 1)
        glEnd()
        glEndList()
        glEnable(GL_DEPTH_TEST)

        return genList

    def make_axis(self):
        genList = glGenLists(1)
        glNewList(genList, GL_COMPILE)

        glLineWidth(5)

        glBegin(GL_LINES)

        glColor3f(1, 0, 0)
        glVertex3d(-10, -10, 0)
        glVertex3d(-9, -10, 0)

        glColor3f(0, 1, 0)
        glVertex3d(-10, -10, 0)
        glVertex3d(-10, -9, 0)

        glColor3f(0, 0, 1)
        glVertex3d(-10, -10, 0)
        glVertex3d(-10, -10, 1)

        glEnd()
        glEndList()

        return genList

    def draw_background_texture(self):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        viewport = glGetIntegerv( GL_VIEWPORT )
        glOrtho(0.0, viewport[2], 0.0, viewport[3], -1.0, 1.0)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()

        glLoadIdentity()
        glDisable(GL_LIGHTING)
        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)

        glColor3f(1,1,1)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.image_background)

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex3f(0, 0, 0)

        glTexCoord2f(0, 1)
        glVertex3f(0, viewport[3], 0)

        glTexCoord2f(1, 1)
        glVertex3f(viewport[2], viewport[3], 0)

        glTexCoord2f(1, 0)
        glVertex3f(viewport[2], 0, 0)
        glEnd()

        glEnable(GL_DEPTH_TEST)

        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()

        glMatrixMode(GL_MODELVIEW)

    def draw_tools(self, picking=False):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        viewport = glGetIntegerv( GL_VIEWPORT )
        glOrtho(0.0, viewport[2], 0.0, viewport[3], -1.0, 1.0)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()

        sW = viewport[2]
        sH = viewport[3]

        glLoadIdentity()
        glDisable(GL_LIGHTING)
        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)

        glColor3f(1,1,1)
        #glBindTexture(GL_TEXTURE_2D, self.selectTool.texture)
        sH = sW
        for tool in [self.moveTool, self.rotateTool, self.scaleTool]:
            if picking:
                glColor3ub(tool.color_id[0], tool.color_id[1], tool.color_id[2])
                glEnable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, self.tool_background)
            else:
                glEnable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, tool.texture)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0)
            glVertex3f(tool.position[0] * (sW*.01), tool.position[1]* (sH*.01), 0)

            glTexCoord2f(0, 1)
            glVertex3f(tool.position[0] * (sW*.01), (tool.position[1]+tool.size[1]) * (sH*.01), 0)

            glTexCoord2f(1, 1)
            glVertex3f((tool.position[0]+tool.size[0]) * (sW*.01), (tool.position[1]+tool.size[1]) * (sH*.01), 0)

            glTexCoord2f(1, 0)
            glVertex3f((tool.position[0]+tool.size[0]) * (sW*.01), tool.position[1]* (sH*.01), 0)
            glEnd()
            if tool.pressed and not picking:
                glDisable(GL_TEXTURE_2D)
                glColor3f(1.,.0,.0)
                glBegin(GL_LINE_LOOP)
                glVertex3f(tool.position[0] * (sW*.01), tool.position[1]* (sH*.01), 0)
                glVertex3f(tool.position[0] * (sW*.01), (tool.position[1]+tool.size[1]) * (sH*.01), 0)
                glVertex3f((tool.position[0]+tool.size[0]) * (sW*.01), (tool.position[1]+tool.size[1]) * (sH*.01), 0)
                glVertex3f((tool.position[0]+tool.size[0]) * (sW*.01), tool.position[1]* (sH*.01), 0)
                glEnd()


        glEnable(GL_DEPTH_TEST)

        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()

        glMatrixMode(GL_MODELVIEW)


    def normalize_angle(self, angle):
        while angle < 0:
            angle += 360 * 16
        while angle > 360 * 16:
            angle -= 360 * 16
        return angle

    def normalize_angle_x(self, angle):
        if angle < 0:
            angle = 0
        if angle > 180:
            angle = 180
        return angle


def _gl_vector(array, *args):
    '''
    Convert an array and an optional set of args into a flat vector of GLfloat
    '''
    array = numpy.array(array)
    if len(args) > 0:
        array = numpy.append(array, args)
    vector = (GLfloat * len(array))(*array)
    return vector