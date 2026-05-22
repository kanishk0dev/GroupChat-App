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

    const button =
    document.getElementById("theme-btn");

    // dark mode

    if(savedTheme === "dark"){

        document.documentElement
        .classList.add("dark-theme");

        if(button){

            button.innerHTML = "☀️";
        }
    }

    // light mode

    else{

        document.documentElement
        .classList.remove("dark-theme");

        if(button){

            button.innerHTML = "🌙";
        }
    }
}


// ---------------- TOGGLE THEME ----------------

function toggleTheme(){

    const button =
    document.getElementById("theme-btn");

    document.documentElement
    .classList.toggle("dark-theme");

    // save dark

    if(document.documentElement
       .classList.contains("dark-theme")){

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