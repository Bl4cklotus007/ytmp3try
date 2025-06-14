document.addEventListener('DOMContentLoaded', function() {
    const videoUrl = document.getElementById('videoUrl');
    const getInfoBtn = document.getElementById('getInfoBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const videoPreview = document.getElementById('videoPreview');
    const thumbnail = document.getElementById('thumbnail');
    const videoTitle = document.getElementById('videoTitle');
    const errorMessage = document.getElementById('errorMessage');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const historyList = document.getElementById('historyList');

    let currentVideoInfo = null;

    // Load download history
    loadHistory();

    // Get video info when button is clicked
    getInfoBtn.addEventListener('click', getVideoInfo);
    videoUrl.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            getVideoInfo();
        }
    });

    // Handle download button click
    downloadBtn.addEventListener('click', downloadVideo);

    async function getVideoInfo() {
        const url = videoUrl.value.trim();
        if (!url) {
            showError('Please enter a YouTube URL');
            return;
        }

        showLoading();
        hideError();
        videoPreview.classList.add('d-none');

        try {
            console.log('Sending request with URL:', url);
            
            // Try POST request first
            let response = await fetch('/get_video_info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ url: url })
            });

            // If POST fails, try GET request
            if (!response.ok) {
                console.log('POST request failed, trying GET request');
                response = await fetch(`/get_video_info?url=${encodeURIComponent(url)}`, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json'
                    }
                });
            }

            console.log('Response status:', response.status);
            const data = await response.json();
            console.log('Response data:', data);

            if (response.ok) {
                currentVideoInfo = data;
                displayVideoInfo(data);
            } else {
                showError(data.error || 'Failed to get video info');
            }
        } catch (error) {
            console.error('Error:', error);
            showError('Network error. Please try again.');
        } finally {
            hideLoading();
        }
    }

    function displayVideoInfo(info) {
        thumbnail.src = info.thumbnail;
        videoTitle.textContent = info.title;
        videoPreview.classList.remove('d-none');
    }

    async function downloadVideo() {
        if (!currentVideoInfo) {
            showError('Please get video info first');
            return;
        }

        showLoading();
        hideError();

        try {
            console.log('Sending download request:', {
                url: videoUrl.value,
                format: 'mp3'
            });

            const response = await fetch('/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    url: videoUrl.value,
                    format: 'mp3'
                })
            });

            console.log('Download response status:', response.status);
            const data = await response.json();
            console.log('Download response data:', data);

            if (response.ok) {
                // Trigger file download with the video title
                const downloadLink = document.createElement('a');
                downloadLink.href = `/download_file/${data.filename}`;
                downloadLink.download = data.title + '.mp3';
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
                
                // Reload history
                loadHistory();
                
                // Reset form
                videoUrl.value = '';
                videoPreview.classList.add('d-none');
                currentVideoInfo = null;
            } else {
                showError(data.error || 'Download failed');
            }
        } catch (error) {
            console.error('Error:', error);
            showError('Network error. Please try again.');
        } finally {
            hideLoading();
        }
    }

    async function loadHistory() {
        try {
            const response = await fetch('/get_history');
            const history = await response.json();
            
            historyList.innerHTML = '';
            history.reverse().forEach(item => {
                const listItem = document.createElement('a');
                listItem.href = `/download_file/${item.filename}`;
                listItem.className = 'list-group-item list-group-item-action';
                listItem.innerHTML = `
                    <div class="d-flex w-100 justify-content-between">
                        <h5 class="mb-1">${item.title}</h5>
                        <small>${item.timestamp}</small>
                    </div>
                    <p class="mb-1">Format: MP3</p>
                `;
                historyList.appendChild(listItem);
            });
        } catch (error) {
            console.error('Failed to load history:', error);
        }
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('d-none');
        // Scroll to error message
        errorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function hideError() {
        errorMessage.classList.add('d-none');
    }

    function showLoading() {
        loadingSpinner.classList.remove('d-none');
        getInfoBtn.disabled = true;
        downloadBtn.disabled = true;
    }

    function hideLoading() {
        loadingSpinner.classList.add('d-none');
        getInfoBtn.disabled = false;
        downloadBtn.disabled = false;
    }
}); 