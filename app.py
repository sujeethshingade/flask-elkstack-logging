import os
import json
import time
import socket
import logging
import datetime
import threading
import random
import psutil
from faker import Faker
from flask import Flask, request, render_template, jsonify

app = Flask(__name__)
fake = Faker()

# Simple TCP socket sender
def send_log_to_logstash(log_data):
    try:
        # Add timestamp if not present
        if 'timestamp' not in log_data:
            log_data['timestamp'] = datetime.datetime.now().isoformat()

        # Convert to JSON
        log_json = json.dumps(log_data)

        # Create socket connection to Logstash
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)  # Add timeout

        # Connect to Logstash
        logstash_host = os.environ.get('LOGSTASH_HOST', 'logstash')
        logstash_port = int(os.environ.get('LOGSTASH_PORT', 5000))

        sock.connect((logstash_host, logstash_port))
        sock.sendall((log_json + '\n').encode())
        sock.close()

        # Only print summary logs (to avoid console overload)
        if 'summary' in log_data.get('message', '').lower():
            print(f"Log sent to Logstash: {log_json[:200]}...")

    except Exception as e:
        print(f"Error sending log to Logstash: {e}")

# Setup standard logging for console output
logger = logging.getLogger('flask-app')
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# Flask routes
@app.route('/')
def home():
    username = request.args.get('username', 'anonymous')

    log_data = {
        'timestamp': datetime.datetime.now().isoformat(),
        'hostname': socket.gethostname(),
        'server_name': socket.gethostname(),
        'username': username,
        'app_name': 'flask-app',
        'container_id': 1,
        'log_level': 'INFO',
        'message': f"Home page accessed by {username}",
        'request_url': '/',
        'parameters': '',
        'path': '/',
        'method': request.method,
        'ip': request.remote_addr,
        'random_number': random.randint(1, 1000),
        'rotation_test': True
    }

    send_log_to_logstash(log_data)
    logger.info(f"Home page accessed by {username}")

    return render_template('index.html')

@app.route('/generate')
def start_generation():
    username = request.args.get('username', 'system')
    size_mb = float(request.args.get('size_mb', 10))

    log_data = {
        'timestamp': datetime.datetime.now().isoformat(),
        'hostname': socket.gethostname(),
        'server_name': socket.gethostname(),
        'username': username,
        'app_name': 'flask-app',
        'container_id': 1,
        'log_level': 'INFO',
        'message': f"Starting log generation: {size_mb}MB by {username}",
        'request_url': '/generate',
        'parameters': f'size_mb={size_mb}',
        'path': '/generate',
        'method': request.method,
        'ip': request.remote_addr,
        'random_number': random.randint(1, 1000),
        'rotation_test': True
    }

    send_log_to_logstash(log_data)
    logger.info(f"Starting log generation: {size_mb}MB by {username}")

    # Start generation in a background thread
    thread = threading.Thread(target=generate_logs_of_size, args=(size_mb,))
    thread.daemon = True
    thread.start()

    return f"Started generating {size_mb}MB of logs in the background. Check Kibana for progress or look at the logstash container logs for rotations."

def generate_logs_of_size(target_size_mb):
    """Generate logs of approximately the specified size in MB"""
    target_size_bytes = target_size_mb * 1024 * 1024
    total_size = 0
    total_count = 0
    start_time = time.time()

    batch_size = 100 if target_size_mb >= 10 else 10  # Batch size based on target
    log_batches = []

    # Generate random data for log fields
    log_levels = ['INFO', 'DEBUG', 'ERROR', 'WARN', 'TRACE']
    usernames = [fake.user_name() for _ in range(10)]
    app_names = ["app1", "app2", "app3"]
    request_urls = ["/home", "/about", "/contact", "/faq", "/services"]
    methods = ['GET', 'POST', 'PUT', 'DELETE']
    ips = [fake.ipv4() for _ in range(10)]

    message_templates = [
        "User {username} accessed {page} page",
        "API request to {endpoint} completed in {time}ms",
        "Database query executed in {time}ms with result count: {count}",
        "File upload by {username} completed. File size: {size}KB",
        "User {username} logged in from IP {ip}",
        "Cache hit ratio: {ratio}% for query {query}",
        "Memory usage: {memory}MB, CPU: {cpu}%",
        "Background job {job_id} completed in {time}ms"
    ]

    logger.info(f"Starting log generation for {target_size_mb}MB of logs")

    try:
        current_batch = []
        batch_start_time = time.time()

        while total_size < target_size_bytes:
            # Create a random log message
            template = random.choice(message_templates)
            message = template.format(
                username=random.choice(usernames),
                page=random.choice(request_urls),
                endpoint=f"/api/{random.choice(['users', 'products', 'orders'])}/{random.randint(1, 9999)}",
                time=random.randint(1, 5000),
                count=random.randint(0, 1000),
                size=random.randint(10, 5000),
                ip=random.choice(ips),
                ratio=random.randint(1, 100),
                query=f"SELECT * FROM {random.choice(['users', 'products', 'orders'])} WHERE id = {random.randint(1, 9999)}",
                memory=random.randint(100, 8000),
                cpu=random.randint(1, 100),
                job_id=f"job-{random.randint(1000, 9999)}"
            )

            # Calculate target entry size based on progress
            progress_ratio = total_size / target_size_bytes
            additional_field_count = int(10 * progress_ratio) + 1
            
            # Generate random additional fields to make the log entry bigger
            additional_fields = {}
            for i in range(additional_field_count):
                field_name = f"field_{i}"
                # Make field size larger as we get closer to target
                field_size = random.randint(50, 200 + int(800 * progress_ratio))
                additional_fields[field_name] = fake.text(max_nb_chars=field_size)

            # Create the log entry
            log_data = {
                'timestamp': datetime.datetime.now().isoformat(),
                'hostname': socket.gethostname(),
                'server_name': socket.gethostname(),
                'username': random.choice(usernames),
                'app_name': random.choice(app_names),
                'container_id': random.randint(1, 100),
                'log_level': random.choice(log_levels),
                'message': message,
                'request_url': random.choice(request_urls),
                'parameters': f"param{random.randint(1,5)}=value{random.randint(1,100)}",
                'path': random.choice(request_urls),
                'method': random.choice(methods),
                'ip': random.choice(ips),
                'random_number': random.randint(1, 10000),
                'rotation_test': True,
                **additional_fields
            }

            # Convert to JSON to calculate size
            log_json = json.dumps(log_data)
            entry_size = len(log_json.encode('utf-8'))

            # Add to batch
            current_batch.append(log_data)
            
            # Update counters
            total_size += entry_size
            total_count += 1

            # Send batch if it's full or if we're close to target
            if len(current_batch) >= batch_size or total_size >= target_size_bytes:
                for log in current_batch:
                    send_log_to_logstash(log)
                
                current_batch = []
                
                # Progress logging
                progress_mb = total_size / (1024 * 1024)
                percent = (progress_mb / target_size_mb) * 100
                
                # Only log every 5% or so to avoid spamming
                if int(percent) % 5 == 0:
                    logger.info(f"Generated {total_count} logs ({progress_mb:.2f}MB / {percent:.1f}%)")
                    
                    # Send progress status to logstash
                    progress_log = {
                        'timestamp': datetime.datetime.now().isoformat(),
                        'hostname': socket.gethostname(),
                        'server_name': socket.gethostname(),
                        'username': 'system',
                        'app_name': 'flask-app',
                        'container_id': 1,
                        'log_level': 'INFO',
                        'message': f"Log generation progress: {total_count} logs ({progress_mb:.2f}MB / {percent:.1f}%)",
                        'request_url': '/generate',
                        'parameters': f'size_mb={target_size_mb}',
                        'path': '/generate',
                        'method': 'GET',
                        'ip': '127.0.0.1',
                        'random_number': random.randint(1, 1000),
                        'rotation_test': True
                    }
                    send_log_to_logstash(progress_log)
                
                # Brief pause between batches to reduce CPU load
                if total_count % (batch_size * 10) == 0:
                    time.sleep(0.1)

        elapsed_time = time.time() - start_time
        logger.info(
            f"Log generation completed: {total_count} logs ({total_size/(1024*1024):.2f}MB) in {elapsed_time:.2f} seconds")

        # Send a final summary log
        summary_log = {
            'timestamp': datetime.datetime.now().isoformat(),
            'hostname': socket.gethostname(),
            'server_name': socket.gethostname(),
            'username': 'system',
            'app_name': 'flask-app',
            'container_id': 1,
            'log_level': 'INFO',
            'message': f"Log generation summary: {total_count} logs ({total_size/(1024*1024):.2f}MB) in {elapsed_time:.2f} seconds",
            'request_url': '/generate',
            'parameters': f'size_mb={target_size_mb}',
            'path': '/generate',
            'method': 'GET',
            'ip': '127.0.0.1',
            'random_number': random.randint(1, 1000),
            'rotation_test': True
        }
        send_log_to_logstash(summary_log)

    except Exception as e:
        logger.error(f"Error during log generation: {str(e)}")
        # Send error log
        error_log = {
            'timestamp': datetime.datetime.now().isoformat(),
            'hostname': socket.gethostname(),
            'server_name': socket.gethostname(),
            'username': 'system',
            'app_name': 'flask-app',
            'container_id': 1,
            'log_level': 'ERROR',
            'message': f"Log generation error: {str(e)}",
            'request_url': '/generate',
            'parameters': f'size_mb={target_size_mb}',
            'path': '/generate',
            'method': 'GET',
            'ip': '127.0.0.1',
            'random_number': random.randint(1, 1000),
            'rotation_test': True
        }
        send_log_to_logstash(error_log)

if __name__ == '__main__':
    logger.info("Flask application starting")
    app.run(host='0.0.0.0', port=5000)