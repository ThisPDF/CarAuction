function startCountdown(endTime, elementId) {
    const timerElement = document.getElementById(elementId);
    const interval = setInterval(() => {
        const now = new Date().getTime();
        const distance = new Date(endTime).getTime() - now;

        if (distance <= 0) {
            clearInterval(interval);
            timerElement.innerHTML = "Auction Ended";
        } else {
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000)) / 1000);
            timerElement.innerHTML = `${hours}h ${minutes}m ${seconds}s`;
        }
    }, 1000);
}
