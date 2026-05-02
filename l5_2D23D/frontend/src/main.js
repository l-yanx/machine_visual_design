import { createScene } from './scene.js';
import { loadMesh, loadPointCloud } from './loaders.js';
import { createCameraMarkers } from './camera_poses.js';
import { setupUI, updateInfoPanel } from './ui.js';

const container = document.getElementById('canvas-container');
const { scene, camera, renderer, controls } = createScene(container);

const state = {
    meshModel: null,
    denseCloud: null,
    sparseCloud: null,
    cameraGroup: null,
};

const assets = {
    modelGltf: '/assets/model.glb',
    densePly: '/assets/dense.ply',
    sparsePly: '/assets/sparse.ply',
    camerasJson: '/assets/cameras.json',
};

async function loadAll() {
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');

    const updateLoading = (msg) => { loadingText.textContent = msg; };

    try {
        updateLoading('加载网格模型...');
        const meshResult = await loadMesh(scene, assets.modelGltf);
        if (meshResult.success) {
            state.meshModel = meshResult.model;
            updateInfoPanel({
                meshText: `glTF · ${numberWithCommas(meshResult.triangleCount)} 三角形`,
            });
        } else {
            // Try OBJ fallback via three.js OBJLoader
            updateLoading('GLB 加载失败，尝试 OBJ...');
            try {
                const { OBJLoader } = await import('three/addons/loaders/OBJLoader.js');
                const objLoader = new OBJLoader();
                const objModel = await objLoader.loadAsync('/assets/model.obj');
                objModel.name = 'mesh';
                objModel.visible = true;
                objModel.traverse((child) => {
                    if (child.isMesh) {
                        child.material = new THREE.MeshStandardMaterial({
                            color: 0x8899aa,
                            roughness: 0.6,
                            metalness: 0.1,
                            side: THREE.DoubleSide,
                        });
                    }
                });
                scene.add(objModel);
                state.meshModel = objModel;
                updateInfoPanel({
                    meshText: 'OBJ 已加载 (回退)',
                });
            } catch (objErr) {
                console.error('OBJ fallback also failed:', objErr);
                updateInfoPanel({ meshText: '加载失败' });
            }
        }

        updateLoading('加载密集点云...');
        const denseResult = await loadPointCloud(scene, assets.densePly, 'dense', 0x66aacc, 3);
        state.denseCloud = denseResult.points;
        updateInfoPanel({ denseText: numberWithCommas(denseResult.count) + ' 点' });

        updateLoading('加载稀疏点云...');
        const sparseResult = await loadPointCloud(scene, assets.sparsePly, 'sparse', 0xff9966, 3);
        state.sparseCloud = sparseResult.points;
        updateInfoPanel({ sparseText: numberWithCommas(sparseResult.count) + ' 点' });

        updateLoading('加载相机位姿...');
        try {
            const resp = await fetch(assets.camerasJson);
            const camData = await resp.json();
            const camResult = createCameraMarkers(scene, camData);
            state.cameraGroup = camResult.group;
            updateInfoPanel({ cameraText: camResult.cameraCount + ' 个' });
        } catch (camErr) {
            console.warn('Camera pose loading failed:', camErr);
            updateInfoPanel({ cameraText: '加载失败' });
        }

        updateLoading('就绪');
        loadingOverlay.classList.add('hidden');
    } catch (err) {
        console.error('Loading failed:', err);
        loadingText.textContent = '加载失败: ' + err.message;
    }
}

function numberWithCommas(x) {
    return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

setupUI(state);

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

loadAll();
animate();
