let intervalId;
        let startTime;
        const duration = 60; // Duration in seconds
        let hourlyData = Array(24).fill(0);
        let dailyData = Array(7).fill(0);

        // Load data from local storage on page load
        window.onload = function() {
            loadDataFromLocalStorage();
            updateCharts();
        };

        function loadDataFromLocalStorage() {
            const storedHourlyData = localStorage.getItem('hourlyData');
            const storedDailyData = localStorage.getItem('dailyData');

            if (storedHourlyData) {
                hourlyData = JSON.parse(storedHourlyData);
            }
            if (storedDailyData) {
                dailyData = JSON.parse(storedDailyData);
            }
        }

        function saveDataToLocalStorage() {
            localStorage.setItem('hourlyData', JSON.stringify(hourlyData));
            localStorage.setItem('dailyData', JSON.stringify(dailyData));
        }

        function showPage(pageId) {
            document.querySelectorAll('#pages > div').forEach(page => page.classList.remove('active'));
            document.getElementById(pageId).classList.add('active');
            if (pageId === 'statistics') {
                updateCharts();
            }
        }

        function startDetection() {
            axios.get('/start_detection')
                .then(response => {
                    console.log(response.data.status);
                    document.getElementById('overlay').textContent = 'Status: Detecting';
                    document.getElementById('startBtn').disabled = true;
                    document.getElementById('stopBtn').disabled = false;
                    startTime = new Date().getTime();
                    updateCount();
                    intervalId = setInterval(updateCount, 1000);
                })
                .catch(error => console.error('Error:', error));
        }
        
        function stopDetection() {
            axios.get('/stop_detection')
                .then(response => {
                    console.log(response.data.status);
                    clearInterval(intervalId);
                    document.getElementById('overlay').textContent = 'Status: Idle';
                    document.getElementById('startBtn').disabled = false;
                    document.getElementById('stopBtn').disabled = true;
                    document.getElementById('progressFill').style.width = '0%';
                })
                .catch(error => console.error('Error:', error));
        }
        
        function updateCount() {
            axios.get('/get_count')
                .then(response => {
                    const result = response.data;
                    const countElement = document.getElementById('countText');
                    const progressFill = document.getElementById('progressFill');
                    
                    if (result.time_up) {
                        countElement.textContent = `Potholes detected in the last minute: ${result.count}`;
                        progressFill.style.width = '100%';
                        clearInterval(intervalId);
                        document.getElementById('startBtn').disabled = false;
                        document.getElementById('stopBtn').disabled = true;
                        document.getElementById('overlay').textContent = 'Status: Completed';
                        updateStatistics(result.count);
                    } else {
                        const elapsedTime = (new Date().getTime() - startTime) / 1000;
                        const progress = (elapsedTime / duration) * 100;
                        countElement.textContent = `Current pothole count: ${result.count}`;
                        progressFill.style.width = `${progress}%`;
                    }
                })
                .catch(error => console.error('Error:', error));
        }

        function updateStatistics(count) {
            const now = new Date();
            hourlyData[now.getHours()] += count;
            dailyData[now.getDay()] += count;
            saveDataToLocalStorage();
            updateCharts();
        }

        function updateCharts() {
            updateHourlyChart();
            updateDailyChart();
        }

        function updateHourlyChart() {
            const ctx = document.getElementById('hourlyChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: Array.from({length: 24}, (_, i) => `${i}:00`),
                    datasets: [{
                        label: 'Potholes Detected',
                        data: hourlyData,
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }

        function updateDailyChart() {
            const ctx = document.getElementById('dailyChart').getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
                    datasets: [{
                        label: 'Potholes Detected',
                        data: dailyData,
                        backgroundColor: 'rgba(75, 192, 192, 0.6)'
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
