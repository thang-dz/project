const container = document.getElementById("container");
const registerBtn = document.getElementById("register");
const loginBtn = document.getElementById("login");

registerBtn.addEventListener("click", () => {
  container.classList.add("active");
});

loginBtn.addEventListener("click", () => {
  container.classList.remove("active");
});
window.addEventListener('load', function() {
  const alertContainer = document.querySelector('.fixed-alert');
  if (alertContainer) {
      alertContainer.classList.add('show');  // Show the alert
      setTimeout(() => {
          alertContainer.classList.remove('show');  // Hide after 5 seconds
      }, 5000); // Adjust the time as needed
  }
});