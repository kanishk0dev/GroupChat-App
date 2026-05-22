// ---------------- APPLY SAVED THEME ----------------

document.addEventListener(

    "DOMContentLoaded",

    function(){

        applyTheme();
    }
);


// ---------------- APPLY THEME ----------------

function applyTheme(){

    const savedTheme =
    localStorage.getItem("theme");

    const container =
    document.getElementById("container");

    const button =
    document.getElementById("theme-btn");

    // container missing
    if(!container){

        return;
    }

    // dark mode

    if(savedTheme === "dark"){

        container.classList.add("dark-theme");

        if(button){

            button.innerHTML = "☀️";
        }
    }

    // light mode

    else{

        container.classList.remove("dark-theme");

        if(button){

            button.innerHTML = "🌙";
        }
    }
}


// ---------------- TOGGLE THEME ----------------

function toggleTheme(){

    const container =
    document.getElementById("container");

    const button =
    document.getElementById("theme-btn");

    if(!container){

        return;
    }

    container.classList.toggle("dark-theme");

    // save dark

    if(container.classList.contains("dark-theme")){

        localStorage.setItem(

            "theme",

            "dark"
        );

        if(button){

            button.innerHTML = "☀️";
        }
    }

    // save light

    else{

        localStorage.setItem(

            "theme",

            "light"
        );

        if(button){

            button.innerHTML = "🌙";
        }
    }
}