
function createChildren()
{
    let el = document.getElementsByClassName("taxons-hierarchy")[0];
    let children = JSON.parse(this.responseText).value;

    el.innerHTML = '';
    for(let i = 0; i < children.length; i++)
    {
        el.innerHTML += '<a href="/taxa/' + children[i].id + '" class="badge badge-pill badge-primary"><h6>' +  children[i].name + '</h6></a>';
    }


}

function searchParentId(event)
{
    let xhr = new XMLHttpRequest();
    let parentName = encodeURIComponent(event.currentTarget.value);
    if(parentName === "") return;

    let body = 'csrfmiddlewaretoken=' + document.getElementsByName('csrfmiddlewaretoken')[0].value + '&' + 'parentName=' + parentName;

    xhr.open("POST", "/taxa/search", true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onreadystatechange = createChildren;
    xhr.send(body);
}

window.onload = function(e)
{
    let el = document.getElementById("taxonParentId");
    el.addEventListener('keyup', searchParentId);
}