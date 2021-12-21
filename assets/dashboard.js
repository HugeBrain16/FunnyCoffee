function updatePerfStats() {
    $.getJSON("/api/host_machine", (res) => {
        $("#memStat").html(`RAM: <b>${res['memory']['used']}MB</b>`);
        $("#cpuStat").html(`CPU: <b>${res['cpu']['percent'].toFixed(2)}%</b>`);
    });
}

updatePerfStats();
setInterval(updatePerfStats, 10 * 1000);
