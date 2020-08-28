function addParentId(element) {
    let el;
    if (document.getElementsByName("taxonParentName")[0])
        el = document.getElementsByName("taxonParentName")[0];
    else
        el = document.getElementsByName("taxonSearchName")[0];
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
    // for(let i = 0; i < children.length; i++) {
    //     el.innerHTML += '<div onclick="addParentId(this)" data-parentId="'+ children[i].id +
    //         '" class="badge badge-pill badge-primary"><h6>' +  children[i].name + '</h6></div>';
    // }
    for(let i = 0; i < children.length; i++) {
        el.innerHTML += '<div onclick="addParentId(this)" class="badge badge-pill badge-primary"><h6>' +
            children[i] + '</h6></div>';
    }

}

function searchTaxons(event) {
    let xhr = new XMLHttpRequest();
    let taxonName = encodeURIComponent(event.currentTarget.value);
    if(taxonName === "") return;

    let body = 'csrfmiddlewaretoken=' + document.getElementsByName('csrfmiddlewaretoken')[0].value + '&' + 'taxonName=' + taxonName;

    xhr.open("POST", "/taxon/search/", true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onreadystatechange = createChildren;
    xhr.send(body);
}

document.addEventListener('DOMContentLoaded', function ()  {

    let el = document.getElementById("taxonParentName");
    if(el) el.addEventListener('keyup', searchTaxons);

    let taxId = document.getElementById("taxonSearchName");
    if(taxId) taxId.addEventListener('keyup', searchTaxons);

});


function sendExperimentsJson(element)
{
    let dataNMR = [];
    let dataMS = [];
    let dataCSV = [];
    let checkClassNMR, checkClassMS, checkClassCSV, dataType, idInput;
    if(element.currentTarget.dataset.type === 'experiment')
    {
        checkClassNMR = 'exp-check-nmr';
        checkClassMS = 'exp-check-ms';
        checkClassCSV = 'exp-check-csv';
        dataType = 'experiments';
        idInput = 'experiments-id-input';
    }
    else
    {
        checkClassNMR = 'prob-check-nmr';
        checkClassMS = 'prob-check-ms';
        checkClassCSV = 'prob-check-csv';
        dataType = 'probs';
        idInput = 'probs-id-input';
    }


    let trs = document.getElementsByClassName(checkClassNMR);
    for(let item of trs) {
        if(item.checked)
        {
            dataNMR.push({'id': item.dataset.id});
        }
    }

    trs = document.getElementsByClassName(checkClassMS);
    for(let item of trs) {
        if(item.checked)
        {
            dataMS.push({'id': item.dataset.id});
        }
    }

    trs = document.getElementsByClassName(checkClassCSV);
    for(let item of trs) {
        if(item.checked)
        {
            dataCSV.push({'id': item.dataset.id});
        }
    }


    let input = document.getElementsByClassName(idInput)[0];
    let obj = {};
    obj[dataType] = {NMR: dataNMR, MS: dataMS, CSV: dataCSV};
    input.value = JSON.stringify(obj);

    let form = document.getElementsByClassName('id-form')[0];
    form.submit();
}

function getFunctionForUnselect(checkClassNMR, checkClassMS, checkClassCSV)
{
    let classNmr = checkClassNMR, classMs = checkClassMS, classCSV = checkClassCSV;
    return function unselectExperiments()
    {
        let trs = document.getElementsByClassName(classNmr);
        for(let item of trs) {
            item.checked = false;
        }

        trs = document.getElementsByClassName(classMs);
        for(let item of trs) {
            item.checked = false;
        }

        trs = document.getElementsByClassName(classCSV);
        for(let item of trs) {
            item.checked = false;
        }
    }
}


function addCheckboxAndButton(element)
{
    let db = document.getElementsByClassName('download-button')[0];
    if(db) db.remove();

    let downloadButton = document.createElement('button');
    downloadButton.classList.add('btn');
    downloadButton.classList.add('btn-success');
    downloadButton.classList.add('m-2');
    downloadButton.classList.add('download-button');
    downloadButton.onclick = sendExperimentsJson;

    let checkClassNMR, checkClassMS, checkClassCSV, labelClass;
    if(element.dataset.type === 'experiment')
    {
        downloadButton.innerText = 'Download experiments';
        downloadButton.dataset.type = 'experiment'
        checkClassNMR = 'exp-check-nmr';
        checkClassMS = 'exp-check-ms';
        checkClassCSV = 'exp-check-csv';
        labelClass = 'exp-label';
    }
    else
    {
        downloadButton.innerText = 'Download probs';
        downloadButton.dataset.type = 'prob'
        checkClassNMR = 'prob-check-nmr';
        checkClassMS = 'prob-check-ms';
        checkClassCSV = 'prob-check-csv';
        labelClass = 'prob-label';
    }


    let unsB = document.getElementsByClassName('unselect-button')[0];
    if(unsB) unsB.remove();

    let unselectButton = document.createElement('button');
    unselectButton.classList.add('btn');
    unselectButton.classList.add('btn-danger');
    unselectButton.classList.add('m-2');
    unselectButton.classList.add('unselect-button');
    unselectButton.onclick = getFunctionForUnselect(checkClassNMR, checkClassMS, checkClassCSV);
    unselectButton.innerText = 'Unselect';

    document.getElementsByClassName('adding-button')[0].after(unselectButton);
    document.getElementsByClassName('unselect-button')[0].after(downloadButton);

    let trs = document.getElementsByClassName(checkClassNMR);
    for(let item of trs) {
        item.type = 'checkbox';
        item.checked = 'true';
    }

    trs = document.getElementsByClassName(checkClassMS);
    for(let item of trs) {
        item.type = 'checkbox';
        item.checked = 'true';
    }

    trs = document.getElementsByClassName(checkClassCSV);
    for(let item of trs) {
        item.type = 'checkbox';
        item.checked = 'true';
    }

    trs = document.getElementsByClassName(labelClass);
    for(let item of trs) {
        item.hidden = false;
    }
}

function taxonSearch(params, data) {

}

$(document).ready(function () {
    $('.js-taxon-search').select2();
});