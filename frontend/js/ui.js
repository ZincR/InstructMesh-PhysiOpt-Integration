/**
 * UI Module
 * Handles UI state management (loading, errors, viewer visibility)
 */

export class UI {
    static showLoading() {
        document.getElementById('loading-section').classList.remove('hidden');
    }

    static hideLoading() {
        document.getElementById('loading-section').classList.add('hidden');
    }

    static showError(message) {
        document.getElementById('error-text').textContent = message;
        document.getElementById('error-section').classList.remove('hidden');
    }

    static hideError() {
        document.getElementById('error-section').classList.add('hidden');
    }

    static showViewer() {
        document.getElementById('viewer-section').classList.remove('hidden');
    }

    static hideViewer() {
        document.getElementById('viewer-section').classList.add('hidden');
    }

    static showOptimizedViewer() {
        const optimizedWrapper = document.getElementById('optimized-viewer-wrapper');
        if (optimizedWrapper) {
            optimizedWrapper.classList.remove('hidden');
        }
    }

    static hideOptimizedViewer() {
        const optimizedWrapper = document.getElementById('optimized-viewer-wrapper');
        if (optimizedWrapper) {
            optimizedWrapper.classList.add('hidden');
        }
    }

    static updateGenerateButton() {
        const textInput = document.getElementById('text-input');
        const imageUpload = document.getElementById('image-upload');
        const generateBtn = document.getElementById('generate-btn');
        
        const hasText = textInput.value.trim().length > 0;
        const hasImage = imageUpload.files.length > 0;
        
        generateBtn.disabled = !(hasText || hasImage);
    }

    static updateFileName(fileName) {
        const fileNameElement = document.getElementById('file-name');
        if (fileNameElement) {
            fileNameElement.textContent = fileName || 'Choose an image file...';
        }
    }

    static showSegmentationButton() {
        const segmentBtn = document.getElementById('segment-3d-btn');
        if (segmentBtn) {
            segmentBtn.style.display = 'inline-block';
        }
    }

    static showSegmentationInfo() {
        const infoDiv = document.getElementById('segmentation-info');
        if (infoDiv) {
            infoDiv.style.display = 'block';
        }
    }

    static updateSegmentationInstructions(text) {
        const instructions = document.getElementById('segmentation-instructions');
        if (instructions) {
            instructions.textContent = text;
        }
    }

    static showClearSegmentationButton() {
        const clearBtn = document.getElementById('clear-segmentation-btn');
        if (clearBtn) {
            clearBtn.style.display = 'inline-block';
        }
    }

    static updateSegmentButton(text, disabled = false) {
        const segmentBtn = document.getElementById('segment-3d-btn');
        if (segmentBtn) {
            segmentBtn.textContent = text;
            segmentBtn.disabled = disabled;
        }
    }
}
