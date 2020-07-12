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

    xhr.open("POST", "/taxon/search/", true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onreadystatechange = createChildren;
    xhr.send(body);
}

document.addEventListener('DOMContentLoaded', function () {
    let el = document.getElementById("taxonParentName");
    el.addEventListener('keyup', searchParentId);
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
    newNode.append(newNodeHiddenField);

    let newNodeKeyField = document.createElement('input');
    newNodeKeyField.id = 'propKey' + childrenLength;
    newNodeKeyField.setAttribute('data-hiddenid', newNodeHiddenField.id);
    newNodeKeyField.addEventListener('keyup', changePropertyKey);
    newNodeKeyField.classList.add('form-control');

    let labelForKey = document.createElement('label');
    labelForKey.htmlFor = newNodeKeyField.id;
    labelForKey.innerText = 'Ключ ' + childrenLength;

    newNode.children[0].append(labelForKey);
    newNode.children[0].append(newNodeKeyField);


    let newNodeValueField = document.createElement('input');
    newNodeValueField.id = 'propValue' + childrenLength;
    newNodeValueField.setAttribute('data-hiddenid', newNodeHiddenField.id);
    newNodeValueField.addEventListener('keyup', changePropertyValue);
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
        '<input type="number" min="0" placeholder="0" class="form-control" id="pubChemCid' + childrenLength + '" name="pubChemCid' + childrenLength + '"></div>' +
        '<div class="col"><label for="metaName' + childrenLength + '">' + 'Имя метаболита ' + childrenLength + '</label>' +
        '<input type="text" class="form-control" id="metaName' + childrenLength + '" name="metaName' + childrenLength + '"></div>' +
        '<div class="col"><label for="concentration' + childrenLength + '">' + 'Концентрация ' + childrenLength + '</label>' +
        '<input type="number" min="0" placeholder="0" step="0.01" class="form-control" id="concentration' + childrenLength + '" name="concentration' + childrenLength + '"></div>' +
        '<div class="col"><label for="analysisMethod' + childrenLength + '">' + 'Название метода анализа ' + childrenLength + '</label>' +
        '<input type="text" class="form-control" id="analysisMethod' + childrenLength + '" name="analysisMethod' + childrenLength + '"></div>';

    el.append(newNode);
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
            addSimpleField('filepaths', 'filepath', 'Путь')
            break;
    }
}

function deleteLastField(element) {
    let el = document.getElementsByClassName(element.dataset.inputtype)[0];
    el.lastChild.remove();
}