from flask import Flask, render_template, request, jsonify, send_file, flash
import asyncio
from pathlib import Path
from datetime import datetime
import zipfile
import json
import shutil
import os
from werkzeug.utils import secure_filename
from pdf_crawler import PDFCrawler, CONFIG

app = Flask(__name__)
app.secret_key = 'pdf_crawler_secret_key'

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>PDF Crawler</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        textarea, input[type=number] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        textarea { height: 150px; font-family: monospace; }
        .columns { display: flex; gap: 20px; }
        .column { flex: 1; }
        .btn { background: #28a745; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; width: 100%; }
        .btn:hover { background: #218838; }
        .progress { width: 100%; height: 20px; background: #f0f0f0; border-radius: 10px; overflow: hidden; margin: 10px 0; }
        .progress-bar { height: 100%; background: #28a745; transition: width 0.3s ease; }
        .status { text-align: center; margin: 10px 0; font-weight: bold; }
        .results { margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 5px; }
        .metric { background: white; padding: 15px; border-radius: 5px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .file-list { max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; background: white; }
        .file-item { padding: 8px; border-bottom: 1px solid #eee; }
        .file-item:last-child { border-bottom: none; }
        .url-text { color: #666; font-size: 12px; font-style: italic; }
        .hidden { display: none; }
        .search-box { background: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .priority { background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 5px 0; }
        .normal { background: white; border-left: 4px solid #28a745; padding: 10px; margin: 5px 0; }
        .download-section { margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 PDF Crawler</h1>
        <p style="text-align: center; color: #666;">Nhập URL và crawl tất cả file PDF từ website</p>

        <form method="POST" action="/start_crawl">
            <div class="form-group">
                <label>Nhập URLs:</label>
                <textarea name="urls" placeholder="https://example.com/documents&#10;https://another-site.com/papers" required></textarea>
            </div>

            <div class="columns">
                <div class="column">
                    <div class="form-group">
                        <label>Số trang tối đa mỗi site:</label>
                        <input type="number" name="max_pages" value="50" min="1" max="200">
                    </div>
                </div>
                <div class="column">
                    <div class="form-group">
                        <label>Số download đồng thời:</label>
                        <input type="number" name="max_concurrent" value="5" min="1" max="20">
                    </div>
                </div>
                <div class="column">
                    <div class="form-group">
                        <label>Timeout (giây):</label>
                        <input type="number" name="timeout" value="60" min="10" max="180">
                    </div>
                </div>
            </div>

            <button type="submit" class="btn">🚀 Bắt đầu Crawl</button>
        </form>

        <div id="progress-section" class="hidden">
            <div class="status" id="status-text">🔄 Đang khởi tạo crawler...</div>
            <div class="progress">
                <div class="progress-bar" id="progress-bar" style="width: 0%"></div>
            </div>
        </div>

        {% if results %}
        <div class="results">
            <h2>🎉 Kết quả Crawl</h2>

            <div class="columns">
                <div class="column">
                    <div class="metric">
                        <h3>{{ results.sites_processed }}</h3>
                        <p>Sites đã xử lý</p>
                    </div>
                </div>
                <div class="column">
                    <div class="metric">
                        <h3>{{ results.pdfs_found }}</h3>
                        <p>PDFs tìm thấy</p>
                    </div>
                </div>
                <div class="column">
                    <div class="metric">
                        <h3>{{ results.pdfs_downloaded }}</h3>
                        <p>PDFs tải về</p>
                    </div>
                </div>
                <div class="column">
                    <div class="metric">
                        <h3>{{ "%.2f"|format(results.total_size_mb) }} MB</h3>
                        <p>Tổng dung lượng</p>
                    </div>
                </div>
            </div>

            {% if results.pdfs_downloaded > 0 %}
            <div class="download-section">
                <h3>📥 Tải xuống kết quả</h3>

                <div class="search-box">
                    <label><strong>🔍 Tìm kiếm file theo tên và URL:</strong></label>
                    <input type="text" id="search-input" placeholder="Ví dụ: catalog, manual, guide..." style="width: 100%; padding: 8px; margin-top: 5px;">
                    <small>Tìm kiếm trong cả tên file và URL gốc. Ví dụ: 'catalog' sẽ tìm cả file có tên catalog và file có URL chứa catalog</small>
                </div>

                <div class="file-list">
                    <div id="file-list">
                        {% for file in files %}
                        <div class="file-item {{ 'priority' if file.priority else 'normal' }}" data-filename="{{ file.name|lower }}" data-url="{{ file.url|lower }}">
                            <input type="checkbox" id="file_{{ loop.index }}" value="{{ file.path }}">
                            <label for="file_{{ loop.index }}">
                                <strong>{% if file.priority %}🎯 {% else %}📄 {% endif %}{{ file.name }}</strong><br>
                                <span class="url-text">🔗 {{ file.url[:80] }}{% if file.url|length > 80 %}...{% endif %}</span>
                            </label>
                        </div>
                        {% endfor %}
                    </div>
                </div>

                <div style="margin-top: 20px;">
                    <button class="btn" onclick="downloadSelected()">⬇️ Tải file đã chọn</button>
                    <a href="/download_all" class="btn" style="background: #007bff; text-decoration: none; display: inline-block; text-align: center; margin-left: 10px;">⬇️ Tải tất cả</a>
                </div>

                <div style="margin-top: 10px; display: flex; gap: 20px;">
                    <div><strong>Tổng số file:</strong> {{ files|length }}</div>
                    <div><strong>File Ưu tiên:</strong> <span id="priority-count">0</span></div>
                    <div><strong>File khác:</strong> <span id="normal-count">{{ files|length }}</span></div>
                </div>
            </div>
            {% endif %}
        </div>
        {% endif %}
    </div>

    <script>
        function updateProgress(progress, status) {
            document.getElementById('progress-bar').style.width = progress + '%';
            document.getElementById('status-text').textContent = status;
        }

        function filterFiles() {
            const searchTerm = document.getElementById('search-input').value.toLowerCase();
            const fileItems = document.querySelectorAll('.file-item');
            let priorityCount = 0;
            let normalCount = 0;

            fileItems.forEach(item => {
                const filename = item.dataset.filename;
                const url = item.dataset.url;
                const hasKeyword = searchTerm && (filename.includes(searchTerm) || url.includes(searchTerm));

                if (hasKeyword) {
                    item.classList.add('priority');
                    item.classList.remove('normal');
                    item.querySelector('strong').innerHTML = '🎯 ' + item.querySelector('strong').innerHTML.replace(/[🎯📄]\s*/g, '');
                    priorityCount++;
                } else if (searchTerm) {
                    item.classList.add('normal');
                    item.classList.remove('priority');
                    item.querySelector('strong').innerHTML = '📄 ' + item.querySelector('strong').innerHTML.replace(/[🎯📄]\s*/g, '');
                    normalCount++;
                } else {
                    item.classList.add('normal');
                    item.classList.remove('priority');
                    item.querySelector('strong').innerHTML = '📄 ' + item.querySelector('strong').innerHTML.replace(/[🎯📄]\s*/g, '');
                    normalCount++;
                }
            });

            document.getElementById('priority-count').textContent = priorityCount;
            document.getElementById('normal-count').textContent = normalCount;
        }

        document.getElementById('search-input').addEventListener('input', filterFiles);

        function downloadSelected() {
            const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
            if (checkboxes.length === 0) {
                alert('Vui lòng chọn ít nhất một file!');
                return;
            }

            const fileIds = Array.from(checkboxes).map(cb => cb.value);
            fetch('/download_selected', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({files: fileIds})
            }).then(response => response.blob())
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'selected_pdfs.zip';
                a.click();
            });
        }

        // Show progress on form submit
        document.querySelector('form').addEventListener('submit', function() {
            document.getElementById('progress-section').classList.remove('hidden');
            updateProgress(10, '🔄 Đang khởi tạo crawler...');
        });
    </script>
</body>
</html>
    ''')

@app.route('/start_crawl', methods=['POST'])
def start_crawl():
    try:
        # Get form data
        urls_text = request.form['urls']
        max_pages = int(request.form['max_pages'])
        max_concurrent = int(request.form['max_concurrent'])
        timeout = int(request.form['timeout'])

        # Parse URLs
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]

        if not urls:
            flash('⚠️ Vui lòng nhập ít nhất một URL')
            return redirect('/')

        # Update config
        CONFIG["max_pages_per_site"] = max_pages
        CONFIG["max_concurrent_downloads"] = max_concurrent
        CONFIG["timeout"] = timeout

        # Create unique output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path(f"runs/run_{timestamp}")
        output_dir = run_dir / "downloaded_pdfs"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Update CONFIG paths
        CONFIG["output_dir"] = str(output_dir)
        CONFIG["log_file"] = str(run_dir / "pdf_crawler.log")
        CONFIG["metadata_file"] = str(run_dir / "pdf_downloads_metadata.json")
        CONFIG["progress_file"] = str(run_dir / "pdf_crawler_progress.json")

        # Run crawler (synchronous for web app)
        import nest_asyncio
        nest_asyncio.apply()

        crawler = PDFCrawler()
        asyncio.run(crawler.run(urls))

        # Load URL mapping
        url_mapping = {}
        metadata_file = Path(CONFIG["metadata_file"])
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                url_mapping = metadata.get("downloaded_pdfs", {})

        # Prepare file list with URLs
        files = []
        pdf_files = list(output_dir.rglob("*.pdf"))
        pdf_files.sort()

        for pdf_file in pdf_files:
            # Find original URL
            original_url = ""
            for url, filepath in url_mapping.items():
                if Path(filepath).name == pdf_file.name:
                    original_url = url
                    break

            files.append({
                'name': pdf_file.name,
                'path': str(pdf_file),
                'url': original_url,
                'priority': False
            })

        return render_template_string('''
<!DOCTYPE html>
<html>
<head><title>Processing</title></head>
<body>
    <script>
        // Redirect back to main page with results
        window.location.href = '/';
    </script>
</body>
</html>
        ''')

    except Exception as e:
        flash(f'❌ Lỗi: {str(e)}')
        return redirect('/')

@app.route('/download_all')
def download_all():
    try:
        # Find the latest run directory
        runs_dir = Path("runs")
        if not runs_dir.exists():
            return "No runs found", 404

        latest_run = max(runs_dir.iterdir(), key=lambda x: x.stat().st_mtime)
        output_dir = latest_run / "downloaded_pdfs"

        zip_path = latest_run / "all_pdfs.zip"

        # Create zip
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in output_dir.rglob('*'):
                if file.is_file():
                    zipf.write(file, file.relative_to(output_dir))

        return send_file(zip_path, as_attachment=True, download_name=f"all_pdfs_{latest_run.name}.zip")

    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/download_selected', methods=['POST'])
def download_selected():
    try:
        data = request.get_json()
        file_paths = data['files']

        # Find the latest run directory
        runs_dir = Path("runs")
        latest_run = max(runs_dir.iterdir(), key=lambda x: x.stat().st_mtime)

        # Create temp directory
        temp_dir = latest_run / "temp_selected"
        temp_dir.mkdir(exist_ok=True)

        # Copy selected files
        for file_path in file_paths:
            src_path = Path(file_path)
            if src_path.exists():
                dest_path = temp_dir / src_path.name
                shutil.copy2(src_path, dest_path)

        # Create zip
        zip_path = latest_run / "selected_pdfs.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in temp_dir.rglob('*'):
                if file.is_file():
                    zipf.write(file, file.relative_to(temp_dir))

        return send_file(zip_path, as_attachment=True, download_name="selected_pdfs.zip")

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)