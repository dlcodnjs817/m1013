#!/usr/bin/env python3
"""M1013 + 툴 + 상판 + 큐브 + 카메라 2대 — Isaac 씬 한 벌. gen_isaac_demos / eval_isaac_closedloop 공용.

SimulationApp 이 이미 떠 있는 프로세스에서 import 할 것. 규약은 gen_isaac_demos.py 와 동일:
  · 로봇만 물리, 상판·큐브·벽은 시각 전용 (상판 충돌체가 어깨를 막던 09-11 사고 재발 방지)
  · 툴·손목캠·큐브는 운동학 플랜지 fk(q) 에 매 프레임 붙임
  · 정면캠은 cameras_v6match.json 을 상판 상승분만큼 올린 위치
"""
import json, struct
import numpy as np
from isaacsim.core.api import World
from isaacsim.core.api.objects import VisualCuboid
from isaacsim.core.utils.stage import add_reference_to_stage, get_current_stage
from isaacsim.core.prims import SingleArticulation
from isaacsim.core.utils.types import ArticulationAction
from isaacsim.sensors.camera import Camera
from pxr import UsdPhysics, UsdGeom, UsdLux, Gf, Vt
import wristcam_pose as WP

W, H = 640, 480
CUBE = 0.035
AP = 20.955


def quat(R):
    w = np.sqrt(max(0.0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
    return Gf.Quatf(float(w), float((R[2, 1] - R[1, 2]) / (4 * w)), float((R[0, 2] - R[2, 0]) / (4 * w)), float((R[1, 0] - R[0, 1]) / (4 * w)))


def rot_axis(axis, a):
    axis = axis / np.linalg.norm(axis); K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * (K @ K)


def look(eye, tgt):
    f = tgt - eye; f /= np.linalg.norm(f); r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); u = np.cross(r, f)
    T = np.eye(4); T[:3, 0] = r; T[:3, 1] = u; T[:3, 2] = -f; T[:3, 3] = eye; return T


class PickScene:
    def __init__(self, table_z, kin):
        self.table_z, self.kin = table_z, kin
        self.world = World(stage_units_in_meters=1.0, physics_dt=1 / 60, rendering_dt=1 / 60); st = self.stage = get_current_stage()
        add_reference_to_stage("/home/kim/m1013/doosan-robot2/dsr_description2/usd/m1013.usd", "/World/m1013")
        root = [p.GetPath().pathString for p in st.Traverse() if p.GetPath().pathString.startswith("/World/m1013") and p.HasAPI(UsdPhysics.ArticulationRootAPI)][0]
        raw = open('/home/kim/m1013/cad/tool_assembly_flangelocal.stl', 'rb').read(); n = struct.unpack('<I', raw[80:84])[0]
        V = np.frombuffer(raw[84:84 + n * 50], dtype=np.uint8).reshape(n, 50)[:, 12:48].copy().view('<f4').reshape(-1, 3).astype(float) / 1000
        txf = UsdGeom.Xform.Define(st, '/World/tool'); self.t_top, self.t_rop = txf.AddTranslateOp(), txf.AddOrientOp()
        tm = UsdGeom.Mesh.Define(st, '/World/tool/geom'); tm.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*map(float, p)) for p in V]))
        tm.CreateFaceVertexCountsAttr(Vt.IntArray([3] * n)); tm.CreateFaceVertexIndicesAttr(Vt.IntArray(list(range(n * 3))))
        tm.CreateDisplayColorAttr([Gf.Vec3f(0.80, 0.80, 0.84)]); tm.CreateSubdivisionSchemeAttr('none')
        self.art = SingleArticulation(root, name='m1013'); self.world.scene.add(self.art)
        self.sun = UsdLux.DistantLight.Define(st, '/World/sun'); self.sun.CreateIntensityAttr(1200.0)
        self.sun_x = UsdGeom.Xformable(st.GetPrimAtPath('/World/sun')).AddRotateXYZOp(); self.sun_x.Set(Gf.Vec3f(-40, 15, 0))
        self.dome = UsdLux.DomeLight.Define(st, '/World/dome'); self.dome.CreateIntensityAttr(350.0)
        ws = self.world.scene
        ws.add(VisualCuboid('/World/table', name='table', position=np.array([0.705, -0.15, table_z - 0.025]), scale=np.array([1.4, 1.8, 0.05]), color=np.array([0.72, 0.72, 0.70])))
        ws.add(VisualCuboid('/World/wall', name='wall', position=np.array([-0.55, 0.0, 1.25]), scale=np.array([0.05, 4.0, 2.5]), color=np.array([0.92, 0.92, 0.90])))
        ws.add(VisualCuboid('/World/floor', name='floor', position=np.array([0.5, 0, -0.01]), scale=np.array([6, 6, 0.02]), color=np.array([0.55, 0.56, 0.58])))
        self.cube = ws.add(VisualCuboid('/World/cube', name='cube', position=np.array([0.8, -0.25, table_z + CUBE / 2]), size=CUBE, color=np.array([0.1, 0.2, 0.9])))
        self.cam_w = Camera('/World/wristcam', resolution=(W, H)); self.cam_f = Camera('/World/frontcam', resolution=(W, H))
        self.world.reset(); self.cam_w.initialize(); self.cam_f.initialize()
        FC = json.load(open('/home/kim/m1013/cameras_v6match.json'))['front_cam']
        dz = table_z - 0.3746
        self.fc_pos = np.array(FC['pos']) + [0, 0, dz]; self.fc_at = np.array(FC['look_at']) + [0, 0, dz]
        self._intr(self.cam_w, WP.HFOV); self._intr(self.cam_f, FC['hfov_deg'])
        self.idx = np.array([self.art.dof_names.index(f'joint_{i}') for i in range(1, 7)])
        self.ctrl = self.art.get_articulation_controller(); self.ctrl.set_gains(kps=np.full(self.art.num_dof, 1e6), kds=np.full(self.art.num_dof, 2e4))
        self.T_cam_fl = WP.basis(); self.set_frontcam()

    def _intr(self, cam, hfov):
        fmm = AP / 2 / np.tan(np.radians(hfov / 2)); cam.set_focal_length(fmm / 10); cam.set_horizontal_aperture(AP / 10); cam.set_vertical_aperture(AP * 0.75 / 10); cam.set_clipping_range(0.005, 30)

    def set_xf(self, path, T):
        UsdGeom.Xformable(self.stage.GetPrimAtPath(path)).MakeMatrixXform().Set(Gf.Matrix4d(*[float(x) for x in T.T.flatten()]))

    def set_frontcam(self, jitter=np.zeros(3)):
        self.set_xf('/World/frontcam', look(self.fc_pos + jitter, self.fc_at))

    def randomize(self, rng):
        """도메인 무작위화 — 조명·상판색·큐브색·카메라 지터. 정책이 무시해야 할 것들."""
        self.sun.GetIntensityAttr().Set(float(rng.uniform(700, 2000))); self.sun_x.Set(Gf.Vec3f(float(rng.uniform(-70, -25)), float(rng.uniform(-40, 40)), 0))
        self.dome.GetIntensityAttr().Set(float(rng.uniform(150, 600)))
        g = rng.uniform(0.55, 0.85)
        UsdGeom.Gprim(self.stage.GetPrimAtPath('/World/table')).GetDisplayColorAttr().Set([Gf.Vec3f(g + rng.uniform(-0.04, 0.04), g, g - rng.uniform(0, 0.06))])
        UsdGeom.Gprim(self.stage.GetPrimAtPath('/World/cube')).GetDisplayColorAttr().Set([Gf.Vec3f(float(rng.uniform(0.05, 0.25)), float(rng.uniform(0.15, 0.35)), float(rng.uniform(0.75, 1.0)))])
        T = WP.basis(); T[:3, 3] += rng.normal(0, 0.003, 3); rr = rng.normal(0, np.radians(2), 2)
        T[:3, :3] = rot_axis(np.array([1.0, 0, 0]), rr[0]) @ rot_axis(np.array([0, 1.0, 0]), rr[1]) @ T[:3, :3]
        self.T_cam_fl = T; self.set_frontcam(rng.normal(0, 0.01, 3))

    def hold(self, q, n, render):
        for _ in range(n):
            self.ctrl.apply_action(ArticulationAction(joint_positions=q, joint_indices=self.idx)); self.world.step(render=render)

    def teleport(self, q):
        self.art.set_joint_positions(q, joint_indices=self.idx); self.hold(q, 20, False)

    def pose_tool(self, T_fl):
        self.t_top.Set(Gf.Vec3d(*map(float, T_fl[:3, 3]))); self.t_rop.Set(quat(T_fl[:3, :3])); self.set_xf('/World/wristcam', T_fl @ self.T_cam_fl)

    def set_cube(self, T):
        Q = quat(T[:3, :3]); self.cube.set_world_pose(position=T[:3, 3], orientation=np.array([Q.GetReal(), *Q.GetImaginary()]))

    def step_robot(self, q, render=True):
        """관절 q 로 한 프레임 진행 (툴·손목캠 동반). fk 반환."""
        T_fl = self.kin.fk(q); self.pose_tool(T_fl); self.art.set_joint_positions(q, joint_indices=self.idx); self.hold(q, 1, render); return T_fl

    def grab(self, cam):
        rgba = cam.get_rgba()
        for _ in range(60):
            if getattr(rgba, 'ndim', 0) == 3 and rgba.shape[0] > 1: break
            self.world.step(render=True); rgba = cam.get_rgba()
        return rgba[:, :, :3].copy()

    def frames(self):
        return self.grab(self.cam_w), self.grab(self.cam_f)

    def warmup(self, q):
        self.teleport(q); self.pose_tool(self.kin.fk(q))
        for _ in range(400):
            self.hold(q, 1, True); r = self.cam_w.get_rgba()
            if getattr(r, 'ndim', 0) == 3 and r.shape[0] > 1: break
