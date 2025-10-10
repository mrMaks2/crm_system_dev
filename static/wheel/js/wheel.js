document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById('wheelCanvas');
    const ctx = canvas.getContext('2d');
    const spinButton = document.getElementById('spinButton');
    const resultDiv = document.getElementById('result');
    
    // Данные о секторах (будут заполнены с бэкенда)
    let sectors = [];
    
    // Переменные для анимации
    let currentRotation = 0;
    let isSpinning = false;
    
    // Получаем CSRF-токен для AJAX-запросов
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // Функция для загрузки данных о секторах (опционально, если они не встроены в шаблон)
    function loadSectors() {
        // В данном примере сектора передаются через шаблон Django.
        // Если нужно загружать через API, можно сделать fetch-запрос здесь.
        sectors = JSON.parse('{{ sectors_json|escapejs }}');
        drawWheel();
    }
    
    // Функция отрисовки колеса
    function drawWheel() {
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = Math.min(centerX, centerY) - 10;
        const arcAngle = (2 * Math.PI) / sectors.length;
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        sectors.forEach((sector, index) => {
            const startAngle = index * arcAngle + currentRotation;
            const endAngle = (index + 1) * arcAngle + currentRotation;
            
            // Рисуем сектор
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.arc(centerX, centerY, radius, startAngle, endAngle);
            ctx.closePath();
            ctx.fillStyle = sector.color;
            ctx.fill();
            ctx.stroke();
            
            // Добавляем текст
            ctx.save();
            ctx.translate(centerX, centerY);
            ctx.rotate(startAngle + arcAngle / 2);
            ctx.textAlign = 'right';
            ctx.fillStyle = '#000000';
            ctx.font = '14px Arial';
            ctx.fillText(sector.text, radius - 10, 5);
            ctx.restore();
        });
        
        // Рисуем центр колеса
        ctx.beginPath();
        ctx.arc(centerX, centerY, 10, 0, 2 * Math.PI);
        ctx.fillStyle = '#333';
        ctx.fill();
    }
    
    // Функция для вращения колеса
    function spinWheel() {
        if (isSpinning) return;
        
        isSpinning = true;
        spinButton.disabled = true;
        resultDiv.textContent = 'Колесо крутится...';
        
        // Отправляем запрос на сервер
        fetch('/api/spin-wheel/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Получаем индекс выигрышного сектора
                const winningSectorIndex = sectors.findIndex(s => s.id === data.winning_sector.id);
                
                // Вычисляем угол, на который нужно повернуть колесо
                const sectorAngle = 360 / sectors.length;
                const targetRotation = 360 * 5 - (winningSectorIndex * sectorAngle); // 5 полных оборотов + смещение к нужному сектору
                
                // Анимация вращения
                animateRotation(targetRotation, data.winning_sector);
            } else {
                throw new Error(data.error || 'Произошла ошибка');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            resultDiv.textContent = 'Ошибка: ' + error.message;
            isSpinning = false;
            spinButton.disabled = false;
        });
    }
    
    // Функция анимации вращения
    function animateRotation(targetDegrees, winningSector) {
        const duration = 5000; // 5 секунд
        const startTime = performance.now();
        const startRotation = currentRotation;
        
        // Конвертируем градусы в радианы
        const targetRotation = targetDegrees * (Math.PI / 180);
        
        function updateRotation(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Эasing функция для более плавного замедления
            const easeOut = (t) => 1 - Math.pow(1 - t, 3);
            const easedProgress = easeOut(progress);
            
            currentRotation = startRotation + (targetRotation * easedProgress);
            
            drawWheel();
            
            if (progress < 1) {
                requestAnimationFrame(updateRotation);
            } else {
                // Анимация завершена
                isSpinning = false;
                spinButton.disabled = false;
                resultDiv.innerHTML = `
                    <h2>Поздравляем!</h2>
                    <p>Вы выиграли: <strong>${winningSector.text}</strong></p>
                `;
            }
        }
        
        requestAnimationFrame(updateRotation);
    }
    
    // Инициализация
    loadSectors();
    spinButton.addEventListener('click', spinWheel);
});