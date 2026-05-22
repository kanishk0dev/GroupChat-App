function toggleTheme(){

    let container =
    document.getElementById("container");

    let btn =
    document.getElementById("theme-btn");

    container.classList.toggle("dark-theme");

    if(container.classList.contains("dark-theme")){

        btn.innerHTML = "☀️";
    }

    else{

        btn.innerHTML = "🌙";
    }
}