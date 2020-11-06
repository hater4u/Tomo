function processData(){
    let data = JSON.parse(this.responseText);
    if('error' in data){
        console.log(true);
    }
    else {
        console.log(false);
        console.log(data);

        let form = document.getElementById('csvSendForm');

        for(let key in data){
            let field = document.createElement('input');
            field.type = 'hidden';
            field.name = key;
            field.value = data[key];
            form.append(field);
            console.log(key);
        }

        form.submit();
    }
}

function sendCsvFile(event){

    event.preventDefault();
    // event.stopPropagation();

    let formData = new FormData();
    let file = document.getElementsByName("csvFile")[0].files[0];
    formData.append("csvFile", file, file['name']);
    formData.append("csrfmiddlewaretoken", document.getElementsByName('csrfmiddlewaretoken')[0].value);

    let xhr = new XMLHttpRequest();
    xhr.open("POST", "");
    xhr.onreadystatechange = processData;
    xhr.send(formData);
}

document.addEventListener('DOMContentLoaded', function ()  {
    let csvForm = document.getElementById('csvForm');
    if(csvForm){
        csvForm.onsubmit = sendCsvFile;
    }
});

