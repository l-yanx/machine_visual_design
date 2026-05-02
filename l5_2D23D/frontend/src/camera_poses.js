import * as THREE from 'three';

export function createCameraMarkers(scene, camerasJson) {
    const group = new THREE.Group();
    group.name = 'cameras';
    group.visible = false;

    const entries = Object.entries(camerasJson);
    const markerGeo = new THREE.SphereGeometry(0.3, 8, 8);
    const frustumColor = 0x44aaff;

    for (const [name, cam] of entries) {
        const R = new THREE.Matrix3().fromArray(cam.R.flat());
        const t = new THREE.Vector3(cam.t[0], cam.t[1], cam.t[2]);

        // Camera center in world coordinates: C = -R^T * t
        const R4 = new THREE.Matrix4().makeBasis(
            new THREE.Vector3(R.elements[0], R.elements[1], R.elements[2]),
            new THREE.Vector3(R.elements[3], R.elements[4], R.elements[5]),
            new THREE.Vector3(R.elements[6], R.elements[7], R.elements[8]),
        );
        R4.transpose();
        const C = t.clone().applyMatrix3(R).multiplyScalar(-1);

        // Camera center marker
        const markerMat = new THREE.MeshBasicMaterial({ color: frustumColor });
        const marker = new THREE.Mesh(markerGeo, markerMat);
        marker.position.copy(C);
        group.add(marker);

        // Viewing direction indicator (short line from center)
        const dir = new THREE.Vector3(R.elements[6], R.elements[7], R.elements[8]).normalize();
        const arrowOrigin = C.clone().addScaledVector(dir, -1.5);
        const arrowDir = dir.clone().multiplyScalar(2.0);
        const arrowHelper = new THREE.ArrowHelper(
            dir, arrowOrigin, 2.0, 0xff6644, 0.3, 0.15
        );
        group.add(arrowHelper);
    }

    // Connect camera centers with a line (trajectory)
    if (entries.length > 1) {
        const points = [];
        // Sort by name to get sequential order
        const sortedEntries = [...entries].sort((a, b) => a[0].localeCompare(b[0]));
        for (const [name, cam] of sortedEntries) {
            const R = new THREE.Matrix3().fromArray(cam.R.flat());
            const t = new THREE.Vector3(cam.t[0], cam.t[1], cam.t[2]);
            const R4 = new THREE.Matrix4().makeBasis(
                new THREE.Vector3(R.elements[0], R.elements[1], R.elements[2]),
                new THREE.Vector3(R.elements[3], R.elements[4], R.elements[5]),
                new THREE.Vector3(R.elements[6], R.elements[7], R.elements[8]),
            );
            R4.transpose();
            const C = t.clone().applyMatrix3(R).multiplyScalar(-1);
            points.push(C);
        }
        const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
        const lineMat = new THREE.LineBasicMaterial({ color: 0x44aaff, opacity: 0.4, transparent: true });
        const line = new THREE.Line(lineGeo, lineMat);
        group.add(line);
    }

    scene.add(group);
    return { group, cameraCount: entries.length };
}
