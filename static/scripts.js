function addParentId(element) {
    // let el = document.getElementsByName("taxonParentId")[0];
    // el.setAttribute("value", element.dataset.parentid);
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

    xhr.open("POST", "/taxon/search/", true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onreadystatechange = createChildren;
    xhr.send(body);
}

document.addEventListener('DOMContentLoaded', function ()  {
    let n =  new Date();
    let y = n.getFullYear();
    let m = n.getMonth() + 1;
    let d = n.getDate();
    let withdrawDate = document.getElementsByClassName("setdate")[0];
    if(withdrawDate) withdrawDate.value = y.toString() + "-" + m.toString().padStart(2, "0") + "-" + d.toString().padStart(2, "0");

    let form1 = document.getElementsByClassName('experiments_form')[0];
    if(form1) form1.onsubmit = sendJson;

    let el = document.getElementById("taxonParentName");
    if(el) el.addEventListener('keyup', searchParentId);

    let taxId = document.getElementById("taxonSearchName");
    if(taxId) taxId.addEventListener('keyup', searchParentId);

    let bcs = document.getElementsByClassName('bc-ol');
    if(bcs)
    {
        for(let i = 0; i < bcs.length; i++)
        {
            let id = bcs[i].dataset.id;
            let pathInput = document.getElementById('filepath' + id);
            let paths = pathInput.value.split('/');

            for(let i1 = 0; i1 < paths.length; i1++)
            {
                bcs[i].innerHTML += '<li class="breadcrumb-item">' + paths[i1] + '</li>'
            }

            let filesAndDirs = document.getElementsByClassName('filesdirs'+id)[0];
            if(pathInput.value) filesAndDirs.innerHTML = '<div onclick="backToPreviousDirectory(this)" data-id="'+ id +
                '" class="badge badge-warning"><h6>Назад</h6></div>';
        }
    }
});

function addSimpleField(className, memberName, inText)
{
    let el = document.getElementsByClassName(className)[0];
    let childrenLength = (el.children.length + 1).toString();

    let newNode = document.createElement('div');
    newNode.innerHTML = '<label for="' + memberName + childrenLength + '">' + inText + ' ' + childrenLength + '</label>' +
        '<input type="text" class="form-control" id="' + memberName + childrenLength + '" name="' + className + '">';

    el.append(newNode);
}

function changePropertyKey(element) {
    document.getElementById(element.currentTarget.dataset.hiddenid).name = element.currentTarget.value;
}

function changePropertyValue(element) {
    document.getElementById(element.currentTarget.dataset.hiddenid).value = element.currentTarget.value;
}

function addAdditionalProperty()
{
    let el = document.getElementsByClassName('additionalProperties')[0];
    let childrenLength = (el.children.length + 1).toString();
    let newNode = document.createElement('div');
    newNode.classList.add("form-row");

    let col = document.createElement('div');
    col.classList.add('col');
    newNode.append(col);
    newNode.append(col.cloneNode());

    let newNodeHiddenField = document.createElement('input');
    newNodeHiddenField.type = 'hidden';
    newNodeHiddenField.id = 'hiddenFieldId' + childrenLength;
    newNodeHiddenField.setAttribute('data-keyvalue', "true");
    newNode.append(newNodeHiddenField);

    let newNodeKeyField = document.createElement('input');
    newNodeKeyField.id = 'propKey' + childrenLength;
    newNodeKeyField.setAttribute('data-hiddenid', newNodeHiddenField.id);
    newNodeKeyField.addEventListener('change', changePropertyKey);
    newNodeKeyField.classList.add('form-control');

    let labelForKey = document.createElement('label');
    labelForKey.htmlFor = newNodeKeyField.id;
    labelForKey.innerText = 'Ключ ' + childrenLength;

    newNode.children[0].append(labelForKey);
    newNode.children[0].append(newNodeKeyField);


    let newNodeValueField = document.createElement('input');
    newNodeValueField.id = 'propValue' + childrenLength;
    newNodeValueField.setAttribute('data-hiddenid', newNodeHiddenField.id);
    newNodeValueField.addEventListener('change', changePropertyValue);
    newNodeValueField.classList.add('form-control');

    let labelForValue = document.createElement('label');
    labelForValue.htmlFor = newNodeValueField.id;
    labelForValue.innerText = 'Значение ' + childrenLength;

    newNode.children[1].append(labelForValue);
    newNode.children[1].append(newNodeValueField);

    el.append(newNode);
}

function addMetaboliteField() {
    let el = document.getElementsByClassName('metabolites')[0];
    let childrenLength = (el.children.length + 1).toString();

    let newNode = document.createElement('div');
    newNode.classList.add('form-row');
    newNode.innerHTML = '<div class="col"><label for="pubChemCid' + childrenLength + '">' + 'pubChemCid ' + childrenLength + '</label>' +
        '<input data-metabolite="true" type="number" min="0" value="0" class="form-control" id="pubChemCid' + childrenLength + '" name="pubChemCid' + childrenLength + '" required></div>' +
        '<div class="col"><label for="metaName' + childrenLength + '">' + 'Имя метаболита ' + childrenLength + '</label>' +
        '<input data-metabolite="true" type="text" class="form-control" id="metaName' + childrenLength + '" name="metaName' + childrenLength + '" required></div>' +
        '<div class="col"><label for="concentration' + childrenLength + '">' + 'Концентрация ' + childrenLength + '</label>' +
        '<input data-metabolite="true" type="number" min="0" value="0" step="0.01" class="form-control" id="concentration' + childrenLength + '" name="concentration' + childrenLength + '" required></div>' +
        '<div class="col"><label for="analysisMethod' + childrenLength + '">' + 'Название метода анализа ' + childrenLength + '</label>' +
        '<input data-metabolite="true" type="text" class="form-control" id="analysisMethod' + childrenLength + '" name="analysisMethod' + childrenLength + '" required></div>';

    el.append(newNode);
}

function backToPreviousDirectory(element)
{
    let id = element.dataset.id;
    let fd = document.getElementById('bc' + id);
    fd.childNodes[fd.childNodes.length-1].remove();

    let pathInput = document.getElementById('filepath' + id);

    if(pathInput.value.charAt(pathInput.value.length-1) === '/')
    {
    //    it's directory
        pathInput.value = pathInput.value.slice(0, pathInput.value.length-1)
    }
    let slashIndex = pathInput.value.lastIndexOf('/') + 1;
    // if(slashIndex < 0) slashIndex = 0;
    pathInput.value = pathInput.value.slice(0, slashIndex);

    updateFilesAndDirs(pathInput.value, id);
}

function addPartToPathString(element)
{
    let id = element.dataset.id;
    let bc = document.getElementById('bc' + id);


    let newNode = document.createElement('li');
    newNode.classList.add('breadcrumb-item');
    newNode.innerText = element.textContent;
    bc.append(newNode);

    let pathInput = document.getElementById('filepath' + id);

    if('file' in element.dataset)
    {
        let fd = document.getElementsByClassName('filesdirs' + id)[0];
        // let els = fd.childNodes;
        // let length = els.length
        // for (let i = 0; i < length; i++) {
        //     els[0].remove();
        // }
        fd.innerHTML = '<div onclick="backToPreviousDirectory(this)" data-id="'+ id +
                    '" class="badge badge-pill badge-warning"><h6>Назад</h6></div>';

        pathInput.value += element.textContent;
    }
    else
    {

        pathInput.value += element.textContent + '/';
        updateFilesAndDirs(pathInput.value, id);
    }
}

function getFunctionForUpdateFileField(value)
{
    let id = value.toString();

    return function updateFileField()
    {
        let response = JSON.parse(this.responseText);
        let el = document.getElementsByClassName('filesdirs' + id)[0];

        let els = el.childNodes;
        let length = els.length
        for (let i = 0; i < length; i++) {
            els[0].remove();
        }

        if('error' in response)
        {
            let newNode = document.createElement('div');
            newNode.classList.add('alert');
            newNode.classList.add('alert-danger');
            newNode.innerText = response['error'];
            el.append(newNode);
        }
        else
        {
            let dirs = response['dirs'];

            let pathInput = document.getElementById('filepath' + id);
            if(pathInput.value) el.innerHTML = '<div onclick="backToPreviousDirectory(this)" data-id="'+ id +
                                    '" class="badge badge-warning"><h6>Назад</h6></div>';

            for(let i = 0; i < dirs.length; i++)
            {
                el.innerHTML += '<div onclick="addPartToPathString(this)" data-id="'+ id +
                    '" class="badge badge-primary"><h6>' +  dirs[i] + '</h6></div>';
            }

            let files = response['files'];

            for(let i = 0; i < files.length; i++) {
                el.innerHTML += '<div onclick="addPartToPathString(this)" data-file="true" data-id="'+ id +
                    '" class="badge badge-pill badge-success"><h6>' +  files[i] + '</h6></div>';
            }
        }
    }
}

function updateFilesAndDirs(path, id) {
    let xhr = new XMLHttpRequest();
    let csrftoken = document.getElementsByName('csrfmiddlewaretoken')[0].value;
    let data = 'path=' + path;
    xhr.open('post', '/experiment/searchfile/any/', true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.setRequestHeader("X-CSRFToken", csrftoken);
    xhr.onreadystatechange = getFunctionForUpdateFileField(id);
    xhr.send(data);
}

function addFileField()
{
    let el = document.getElementsByClassName('filepaths')[0];
    let childrenLength = (el.children.length + 1).toString();

    let newHiddenFileField = document.createElement('input');
    newHiddenFileField.type = 'hidden';
    newHiddenFileField.id = 'filepath' + childrenLength;
    newHiddenFileField.name = 'filepaths';



    let newNode = document.createElement('div');
    newNode.append(newHiddenFileField);
    newNode.setAttribute('aria-label', 'breadcrumb');
    newNode.innerHTML += '<label>Путь ' + childrenLength + '</label><ol class="breadcrumb" id="bc' + childrenLength + '"><li class="breadcrumb-item">Корень</li></ol>' +
        '<div class="filesdirs' + childrenLength + '"></div>';
    el.append(newNode);

    updateFilesAndDirs('.', childrenLength);
}

function addAdditionalField(element) {

    switch (element.dataset.inputtype) {
        case 'environmentalFactors':
            addSimpleField('environmentalFactors', 'environmentalFactor', 'Фактор');
            break;
        case 'diseases':
            addSimpleField('diseases', 'disease', 'Заболевание');
            break;
        case 'withdrawConditions':
            addSimpleField('withdrawConditions', 'withdrawCondition', 'Условие забора')
            break;
        case 'comments':
            addSimpleField('comments', 'comment', 'Комментарий')
            break;
        case 'additionalProperties':
            addAdditionalProperty();
            break;
        case 'metabolites':
            addMetaboliteField();
            break;
        case 'filepaths':
            // addSimpleField('filepaths', 'filepath', 'Путь');
            addFileField();
            break;
    }
}

function deleteLastField(element) {
    let el = document.getElementsByClassName(element.dataset.inputtype)[0];
    el.lastChild.remove();
}

function updatePage()  {
    let els = document.getElementsByClassName('response')[0].childNodes;
    let length = els.length
    for (let i = 0; i < length; i++) {
        els[0].remove();
    }

    let response = JSON.parse(this.responseText);

    if('success' in response)
    {
        let newNode = document.createElement('div');
        newNode.classList.add('alert');
        newNode.classList.add('alert-success');
        newNode.innerText = response['success'];
        document.getElementsByClassName('response')[0].append(newNode);
    }
    else
    {
        let length = response['error'].length;
        let container = document.getElementsByClassName('response')[0];
        for(let i = 0; i < length; i++)
        {
            let newNode = document.createElement('div');
            newNode.classList.add('alert');
            newNode.classList.add('alert-danger');
            newNode.innerText = response['error'][i];
            container.append(newNode);
        }
    }
}

function sendJson(e) {
    let form = e.currentTarget;

    e.preventDefault();
    let data = {};
    let i = 0;
    let input;
    while((input = form[i]))
    {
        i++;
        if (input.name) {
            if(input.type === 'radio')
            {
                if(input.checked)
                {
                    data[input.name] = input.value;
                }
                continue;
            }

            if(input.name === "environmentalFactors" || input.name === "diseases" || input.name === "withdrawConditions" || input.name === "comments" || input.name === "filepaths")
            {
                if(!(input.name in data)) data[input.name] = [];

                data[input.name].push(input.value);
                continue;
            }

            if(input.dataset.hasOwnProperty('keyvalue'))
            {
                let obj = {};
                obj[input.name] = input.value;

                if(!('additionalProperties' in data)) data['additionalProperties'] = [];
                data['additionalProperties'].push(obj);
                continue;
            }

            if(input.dataset.hasOwnProperty('metabolite'))
            {
                if(!('metabolites' in data)) data['metabolites'] = [];

                let counter = 0;
                while(input.name[counter]  < '0' || '9' < input.name[counter]) counter++;
                let index = parseInt(input.name.substr(counter), 10);

                if(data['metabolites'][index-1] === undefined) data['metabolites'][index-1] = {};
                data['metabolites'][index-1][input.name.substr(0,counter)] = input.value;

                continue;
            }

            data[input.name] = input.value;
        }
    }

    // console.info(data);
    let xhr = new XMLHttpRequest();
    let csrftoken = document.getElementsByName('csrfmiddlewaretoken')[0].value;
    xhr.open(form.method, form.action, true);
    xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr.setRequestHeader("X-CSRFToken", csrftoken);
    // send the collected data as JSON
    xhr.onreadystatechange = updatePage;
    xhr.send(JSON.stringify(data));
}
