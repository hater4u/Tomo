function addParentId(element) {
    // let el = document.getElementsByName("taxonParentId")[0];
    // el.setAttribute("value", element.dataset.parentid);

    let el = document.getElementsByName("taxonParentName")[0];
    el.value = element.textContent;

    let els = document.getElementsByClassName("taxons-hierarchy")[0].childNodes;
    let length = els.length
    for (let i = 0; i < length; i++) {
        els[0].remove();
    }
}

function createChildren() {
    let el = document.getElementsByClassName("taxons-hierarchy")[0];
    let children = JSON.parse(this.responseText).value;

    el.innerHTML = '';
    for(let i = 0; i < children.length; i++) {
        el.innerHTML += '<div onclick="addParentId(this)" data-parentId="'+ children[i].id +
            '" class="badge badge-pill badge-primary"><h6>' +  children[i].name + '</h6></div>';
    }

}

function searchParentId(event) {
    let xhr = new XMLHttpRequest();
    let parentName = encodeURIComponent(event.currentTarget.value);
    if(parentName === "") return;

    let body = 'csrfmiddlewaretoken=' + document.getElementsByName('csrfmiddlewaretoken')[0].value + '&' + 'parentName=' + parentName;

    xhr.open("POST", "/taxa/search", true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onreadystatechange = createChildren;
    xhr.send(body);
}

document.addEventListener('DOMContentLoaded', function () {
    let el = document.getElementById("taxonParentName");
    el.addEventListener('keyup', searchParentId);
});
