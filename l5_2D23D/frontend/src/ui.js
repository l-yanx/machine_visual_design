export function setupUI(state) {
    const checkboxes = {
        mesh: document.getElementById('show-mesh'),
        dense: document.getElementById('show-dense'),
        sparse: document.getElementById('show-sparse'),
        cameras: document.getElementById('show-cameras'),
    };
    const pointSizeSlider = document.getElementById('point-size');

    function updateVisibility() {
        if (state.meshModel) state.meshModel.visible = checkboxes.mesh.checked;
        if (state.denseCloud) state.denseCloud.visible = checkboxes.dense.checked;
        if (state.sparseCloud) state.sparseCloud.visible = checkboxes.sparse.checked;
        if (state.cameraGroup) state.cameraGroup.visible = checkboxes.cameras.checked;
    }

    function updatePointSize() {
        const size = parseFloat(pointSizeSlider.value);
        if (state.denseCloud && state.denseCloud.material) {
            state.denseCloud.material.size = size;
        }
        if (state.sparseCloud && state.sparseCloud.material) {
            state.sparseCloud.material.size = size;
        }
    }

    for (const [key, cb] of Object.entries(checkboxes)) {
        cb.addEventListener('change', updateVisibility);
    }
    pointSizeSlider.addEventListener('input', updatePointSize);

    return { updateVisibility, updatePointSize };
}

export function updateInfoPanel(info) {
    document.getElementById('info-mesh').textContent = info.meshText || '—';
    document.getElementById('info-dense').textContent = info.denseText || '—';
    document.getElementById('info-sparse').textContent = info.sparseText || '—';
    document.getElementById('info-cameras').textContent = info.cameraText || '—';
}
