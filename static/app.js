let graphCounter = 0;
let elapsedSeconds = 0;   // X-axis will now be 0, 10, 20, 30, ...
function formatTime(seconds) {
  const m = Math.floor(seconds / 60).toString().padStart(2, "0");
  const s = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

// Convert lbs → kg
function lbsToKg(lbs) {
  return lbs * 0.453592;
}

// Calorie calculation function
function calculateCalories(pace, weightKg, elapsedSec) {
  if (elapsedSec === 0 || weightKg === 0) return 0;

  // MET formula based on pace
  const MET = 8 + (pace / 20);
  const minutes = elapsedSec / 60;

  return Math.round(0.0175 * MET * weightKg * minutes);
}

async function update() {
  const c = await fetch("/jump_count").then(r => r.json());
  const t = await fetch("/timer").then(r => r.json());
  const p = await fetch("/pace").then(r => r.json());
  const laps = await fetch("/laps").then(r => r.json());
  const counting = c.counting;
  const goal = Number(document.getElementById("goalInput").value) || 0;

  

  const weightLbs = Number(document.getElementById("weightInput").value) || 0;
  const weightKg = lbsToKg(weightLbs);

  const calories = calculateCalories(p.pace, weightKg, t.time);

  document.getElementById("jumpCount").textContent = c.count;
  document.getElementById("timer").textContent = formatTime(t.time);
  document.getElementById("pace").textContent = `${p.pace} JPM`;
  document.getElementById("calories").textContent = calories;
  

  // Laps
  let lapHtml = "";
  laps.laps.forEach((lap, i) => {
    lapHtml += `
      <div class="lap-entry">
        <span>Lap ${i+1}</span>
        <span>${formatTime(lap.time)} – ${lap.jumps} jumps</span>
      </div>`;
  });
  document.getElementById("calorieGoal").textContent = goal;
  document.getElementById("calorieCurrent").textContent = calories;

  if (goal > 0) {
      const percent = Math.min((calories / goal) * 100, 100);
      document.getElementById("waterFill").style.height = percent + "%";
  } else {
      document.getElementById("waterFill").style.height = "0%";
  }
  // update pace graph
  document.getElementById("laps").innerHTML = lapHtml;

  //reset graph when stopped and cleared
  if (!counting && t.time === 0 && c.count === 0) {
    timeLabels.length = 0;
    paceData.length = 0;
    elapsedSeconds = 0;
    graphCounter = 0;
    chart.update();
}

  if (counting) {
      graphCounter++;
      // Update graph every 10 sec (50 cycles of 200ms)
      if (graphCounter >= 34) {
          elapsedSeconds += 10;      // clean X-axis step
          timeLabels.push(elapsedSeconds);
          paceData.push(p.pace);
          if (timeLabels.length > 120) {
              timeLabels.shift();
              paceData.shift();
          }
          chart.update();
          graphCounter = 0;
      }
  }

}

async function sendCommand(cmd) {
  await fetch(`/${cmd}`, { method: "POST" });
}






















// Update the UI every 200ms
setInterval(update, 300);
update();



// === PACE GRAPH ===
let paceData = [];
let timeLabels = [];
let chart;

// Initialize the chart on page load
function initChart() {
  const ctx = document.getElementById("paceChart").getContext("2d");

  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: timeLabels,
      datasets: [{
        label: "Pace (JPM)",
        data: paceData,
        borderColor: "#5fa8a8",
        backgroundColor: "rgba(143, 207, 207, 0.25)",
        borderWidth: 3,
        fill: true,
        tension: 0.25
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { title: { display: false } },
        y: { beginAtZero: true }
      },
      plugins: {
        legend: {
          labels: { color: "#0f2b2b" }
        }
      }
    }
  });
}

window.onload = initChart;