document.querySelector("button").addEventListener("click", function() {
    alert("Button clicked!");
});
function checkOthers(selectElement, inputId) {
    const otherBox = document.getElementById(inputId);

    if (selectElement.value === "Others" || selectElement.value === "Other") {
        otherBox.style.display = "block";
    } else {
        otherBox.style.display = "none";
    }
}