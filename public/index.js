
const Context = {

    baseApiUrl: localStorage.getItem('BASE_API_URL'),
    authToken: localStorage.getItem('AUTH_TOKEN'),
    doms: {},

}

export default async () => {
    console.log('start app');

    try {
        const response = await fetch(`${Context.baseApiUrl}/auth`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' ,
            'Authorization': `Bearer ${Context.authToken}`
            }
        });
        const data = await response.json();
        console.log(data);
    

    }
    catch (error) {
        console.error('error:', error);
    }  

    
    Context.doms = {
        input_apiUrl: document.querySelector('#apiBaseUrl'),
        input_authToken: document.querySelector('#authToken'),
        btn_save: document.querySelector('#save')
    }

    Context.doms.input_apiUrl.value = Context.baseApiUrl;
    Context.doms.input_authToken.value = Context.authToken;

    Context.doms.btn_save.addEventListener('click', async () => {
        localStorage.setItem('BASE_API_URL', Context.doms.input_apiUrl.value);
        localStorage.setItem('AUTH_TOKEN', Context.doms.input_authToken.value);
        alert('저장되었습니다.');
    }
    );


};