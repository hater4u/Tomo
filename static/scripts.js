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
        el.innerHTML += '<div onclick="addParentId(this)" class="badge badge-pill badge-primary pt-2"><h6>' +
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
            if (item.checked) {
                item.checked = false;
                CheckboxChanged(item);
            }
        }

        trs = document.getElementsByClassName(classMs);
        for(let item of trs) {
            if (item.checked) {
                item.checked = false;
                CheckboxChanged(item);
            }
        }

        trs = document.getElementsByClassName(classCSV);
        for(let item of trs) {
            if (item.checked) {
                item.checked = false;
                CheckboxChanged(item);
            }
        }
    }
}

function functionForCancel(checkClassNMR, checkClassMS, checkClassCSV, labelClass) {
    let classNmr = checkClassNMR, classMs = checkClassMS, classCSV = checkClassCSV, labelCl = labelClass;
    let trs = document.getElementsByClassName(classNmr);
    for(let item of trs) {
        item.hidden = true;
        if (item.checked) {
            item.checked = false;
            CheckboxChanged(item);
        }
    }

    trs = document.getElementsByClassName(classMs);
    for(let item of trs) {
        item.hidden = true;
        if (item.checked) {
            item.checked = false;
            CheckboxChanged(item);
        }
    }

    trs = document.getElementsByClassName(classCSV);
    for(let item of trs) {
        item.hidden = true;
        if (item.checked) {
            item.checked = false;
            CheckboxChanged(item);
        }
    }

    trs = document.getElementsByClassName(labelCl);
    for(let item of trs) {
        item.hidden = true;
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
        downloadButton.innerText = 'Download samples';
        downloadButton.dataset.type = 'prob'
        checkClassNMR = 'prob-check-nmr';
        checkClassMS = 'prob-check-ms';
        checkClassCSV = 'prob-check-csv';
        labelClass = 'prob-label';
    }

    let selB = document.getElementsByClassName('select-button')[0];
    if(selB) selB.remove();

    let selectButton = document.createElement('button');
    selectButton.classList.add('btn');
    selectButton.classList.add('btn-primary');
    selectButton.classList.add('m-2');
    selectButton.classList.add('select-button');
    selectButton.onclick = getFunctionForUnselect(checkClassNMR, checkClassMS, checkClassCSV);
    selectButton.innerText = 'Select all';

    let unsB = document.getElementsByClassName('unselect-button')[0];
    if(unsB) unsB.remove();

    let unselectButton = document.createElement('button');
    unselectButton.classList.add('btn');
    unselectButton.classList.add('btn-secondary');
    unselectButton.classList.add('m-2');
    unselectButton.classList.add('unselect-button');
    unselectButton.onclick = getFunctionForUnselect(checkClassNMR, checkClassMS, checkClassCSV);
    unselectButton.innerText = 'Unselect all';

    let cancelB = document.getElementsByClassName('cancel-button')[0];
    if (cancelB) cancelB.remove();

    let cancelButton = document.createElement('button');
    cancelButton.classList.add('btn');
    cancelButton.classList.add('btn-danger');
    cancelButton.classList.add('m-2');
    cancelButton.classList.add('cancel-button');
    cancelButton.innerText = 'Cancel';

    document.getElementsByClassName('adding-button')[0].after(selectButton);
    document.getElementsByClassName('select-button')[0].after(unselectButton);
    document.getElementsByClassName('unselect-button')[0].after(cancelButton);
    document.getElementsByClassName('cancel-button')[0].after(downloadButton);

    let addb = document.getElementsByClassName('adding-button')[0];
    if(addb) addb.hidden = true;

    let trs = document.getElementsByClassName(checkClassNMR);
    for(let item of trs) {
        item.type = 'checkbox';
        item.hidden = false;
    }

    trs = document.getElementsByClassName(checkClassMS);
    for (let item of trs) {
        item.type = 'checkbox';
        item.hidden = false;
    }

    trs = document.getElementsByClassName(checkClassCSV);
    for (let item of trs) {
        item.type = 'checkbox';
        item.hidden = false;
    }

    trs = document.getElementsByClassName(labelClass);
    for(let item of trs) {
        item.hidden = false;
    }

    let downloadInfo = document.getElementById('downloadInfo');
    downloadInfo.hidden = false;

    selectButton.onclick = function (){
        let trs = document.getElementsByClassName(checkClassNMR);
        for(let item of trs) {
            item.type = 'checkbox';
            if (!item.checked) {
                item.checked = 'true';
                CheckboxChanged(item);
            }
            item.hidden = false;
        }

        trs = document.getElementsByClassName(checkClassMS);
        for (let item of trs) {
            item.type = 'checkbox';
            if (!item.checked) {
                item.checked = 'true';
                CheckboxChanged(item);
            }
            item.hidden = false;
        }

        trs = document.getElementsByClassName(checkClassCSV);
        for (let item of trs) {
            item.type = 'checkbox';
            if (!item.checked) {
                item.checked = 'true';
                CheckboxChanged(item);
            }
            item.hidden = false;
        }
    }

    cancelButton.onclick = function () {
        // let someFunc = getFunctionForUnselect(checkClassNMR, checkClassMS, checkClassCSV);
        // someFunc();
        functionForCancel(checkClassNMR, checkClassMS, checkClassCSV, labelClass);
        downloadButton.remove();
        unselectButton.remove();
        cancelButton.remove();
        selectButton.remove();
        addb.hidden = false;
        downloadInfo.hidden = true;
    }
}

function taxonSearch(params, data) {
    
    // params.term = document.getElementsByName('taxon')
    // If there are no search terms, return all of the data
    if ($.trim(params.term) === '') {
      return data;
    }

    // Do not display the item if there is no 'text' property
    if (typeof data.text === 'undefined') {
      return null;
    }

    // `params.term` should be the term that is used for searching
    // `data.text` is the text that is displayed for the data object
    if (data.text.indexOf(params.term) > -1) {
        let modifiedData = $.extend({}, data, true);
        modifiedData.text += ' (matched)';

      // You can return modified objects from here
      // This includes matching the `children` how you want in nested data sets
      return modifiedData;
    }

    // Return `null` if the term should not be displayed
    return null;
}

// $(document).ready(function () {
//     $('.js-taxon-search-basic').select2();
// });

$(document).ready(function () {
    $('.js-taxon-search-basic').select2({
    // matcher: taxonSearch(),
    ajax: {
        type: 'POST',
        url: '/taxon/search/',
        dataType: 'json',
        // delay: 250,
        data: function (params) {
            return {
                query: params.term,
                csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val()
            };
        },
        processResults: function (data) {
            return {
                results: $.map(data.results, function (obj) {
                    return {
                        id: obj.id, text: obj.name
                    };
                })
            };
        },
        cache: true,
        }
    })
});

//TODO: learn select2 and ajax after rework back and this 2 functions
$(document).ready(function () {
    $('.js-tissue-search-basic').select2({
    ajax: {
        type: 'POST',
        url: '/tissue/search/',
        dataType: 'json',
        // delay: 250,
        data: function (params) {
            return {
                query: params.term,
                csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val()
            };
        },
        processResults: function (data) {
            return {
                results: $.map(data.results, function (obj) {
                    return {
                        id: obj.id, text: obj.name
                    };
                })
            };
        },
        cache: true,
        }
    })
});

function AddMetName2SearchField(event) {
    let metName = event.value;
    let searchField = document.getElementById('metaboliteNames');
    let searchWord = searchField.value;

    if (searchWord){
        searchField.value += ' AND ' + metName;
        searchField.innerText += ' AND ' + metName;
    } else {
        searchField.value = metName;
        searchField.innerText = metName;
    }
}

function showFullTree(event) {
    let tree = document.getElementById('tree');
    let fullTree = document.getElementById('full-tree');
    let showNormalTreeBtn = document.getElementById('showNormalTreeButton');

    tree.hidden = true;
    fullTree.hidden = false;
    showNormalTreeBtn.hidden = false;

}

function showNormalTree(event) {
    let tree = document.getElementById('tree');
    let fullTree = document.getElementById('full-tree');

    tree.hidden = false;
    fullTree.hidden = true;
    event.hidden = true;
}

function CheckboxChanged(event) {
    let elemNumberCSV = document.getElementById('downloadSelectedCSV');
    let elemNumberNMR = document.getElementById('downloadSelectedNMR');
    let elemNumberMS = document.getElementById('downloadSelectedMS');
    if (event.className === 'exp-check-nmr') {
        if (event.checked === true) {
            elemNumberNMR.innerText = (+elemNumberNMR.innerText) + (+event.value);
        } else {
            elemNumberNMR.innerText -= event.value;
        }
    } else if (event.className === 'exp-check-ms') {
        if (event.checked === true) {
            elemNumberMS.innerText = (+elemNumberMS.innerText) + (+event.value);
        } else {
            elemNumberMS.innerText -= event.value;
        }
    } else if (event.className === 'exp-check-csv') {
        if (event.checked === true) {
            elemNumberCSV.innerText = (+elemNumberCSV.innerText) + (+event.value);
        } else {
            elemNumberCSV.innerText -= event.value;
        }
    }
}

$(function () {
  $('[data-toggle="tooltip"]').tooltip()
})
