import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { PLYLoader } from 'three/addons/loaders/PLYLoader.js';

const gltfLoader = new GLTFLoader();
const plyLoader = new PLYLoader();

export async function loadMesh(scene, path) {
    try {
        const gltf = await gltfLoader.loadAsync(path);
        const model = gltf.scene;
        model.name = 'mesh';
        model.visible = true;

        model.traverse((child) => {
            if (child.isMesh) {
                child.material = new THREE.MeshStandardMaterial({
                    vertexColors: true,
                    roughness: 0.6,
                    metalness: 0.1,
                    side: THREE.DoubleSide,
                });
            }
        });

        scene.add(model);

        const triangleCount = countTriangles(model);
        return { model, triangleCount, success: true, format: 'glb' };
    } catch (err) {
        console.warn('GLB load failed, trying OBJ fallback:', err.message);
        // OBJ fallback handled separately
        return { model: null, triangleCount: 0, success: false, error: err.message };
    }
}

function countTriangles(model) {
    let count = 0;
    model.traverse((child) => {
        if (child.isMesh && child.geometry) {
            const idx = child.geometry.index;
            if (idx) {
                count += idx.count / 3;
            } else {
                const pos = child.geometry.attributes.position;
                if (pos) count += pos.count / 3;
            }
        }
    });
    return Math.floor(count);
}

export async function loadPointCloud(scene, path, name, color, pointSize) {
    const geometry = await plyLoader.loadAsync(path);
    geometry.computeBoundingBox();

    let material;
    if (geometry.hasAttribute('color')) {
        material = new THREE.PointsMaterial({
            size: pointSize,
            vertexColors: true,
            sizeAttenuation: true,
        });
    } else {
        material = new THREE.PointsMaterial({
            size: pointSize,
            color: color,
            sizeAttenuation: true,
        });
    }

    const points = new THREE.Points(geometry, material);
    points.name = name;
    points.visible = false;
    scene.add(points);

    return { points, count: geometry.attributes.position.count };
}
