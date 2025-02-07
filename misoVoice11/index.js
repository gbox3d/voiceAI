import express from 'express'
import dotenv from "dotenv"
import https from 'https'
import http from 'http'
import fs from 'fs'
import { MongoClient } from 'mongodb'; // MongoDB 클라이언트 가져오기

import baseApi from './routers/base.js'
import elevenVoiceApi from './routers/elevenvoice.js'

function getPackageVersion() {
  const packageJson = JSON.parse(fs.readFileSync('./package.json', 'utf-8'));
  return packageJson.version;
}

const version = getPackageVersion();
console.log(`Package version: ${version}`);


async function main() {

  dotenv.config({ path: '../.env' }); //환경 변수에 등록 
  console.log(`run mode : ${process.env.NODE_ENV}`);

  const theApp = {
    version: getPackageVersion(),
    eleven_api_key : process.env.ELEVENLABS_API_KEY,
  };

  

  console.log(`eleven_api_key : ${theApp.eleven_api_key}`);


  //mongodb setup
  //mongodb 연결    
  {
    //db name check
    if (!process.env.DB_NAME || process.env.DB_NAME === '') {
      console.log('DB_NAME is not defined');
      process.exit(1);
    }

    const mongoUrl = process.env.MONGO_URL;

    const connectWithRetry = async () => {
      try {
        // const dbclient = await MongoClient.connect(mongoUrl, { useUnifiedTopology: true });
        const dbclient = await MongoClient.connect(mongoUrl); // useUnifiedTopology 제거
        console.log(`Connected successfully to server ${mongoUrl} , DB Name : ${process.env.DB_NAME}`);
        theApp.dbclient = dbclient;
        theApp.dataBase = dbclient.db(process.env.DB_NAME);
      } catch (err) {
        console.log('Failed to connect to MongoDB, retrying in 5 seconds...', err);
        setTimeout(connectWithRetry, 5000);
      }
    };

    await connectWithRetry();

  }

  //admin_key setup
  try {
    const adminkey_doc = await theApp.dataBase.collection('other').findOne({ admin_key: { $exists: true } });
    if (!adminkey_doc) {
      console.log('admin_key is not defined');
      process.exit(1);
    }
    theApp.admin_key = adminkey_doc.admin_key; 
    console.log('admin_key : ', theApp.admin_key);
  }
  catch (err) {
    console.log('Failed to get admin_key', err);
    process.exit(1);
  }

  const app = express()

  //라우터 등록
  const baseApiRouter = baseApi(theApp);
  const elevenVoiceApiRouter = elevenVoiceApi(theApp);
  
  app.use('/api/v1', baseApiRouter);
  app.use('/api/v1/elevenvoice', elevenVoiceApiRouter);
  
  // 에러 핸들링 미들웨어 추가
  app.use((err, req, res, next) => {
    if (err instanceof SyntaxError && err.status === 400 && 'body' in err) {
      console.error('Bad JSON:', err.message);
      return res.status(400).json({ message: 'Invalid JSON payload.' });
    }
    next(err); // 다른 에러는 다음 핸들러로 전달
  });

  //순서 주의 맨 마지막에 나온다.
  app.all('*', (req, res) => {
    res
      .status(404)
      .send('oops! resource not found')
  });

  let baseServer;
  if (process.env.SSL === 'True') {
    console.log(`SSL mode ${process.env.SSL}`);
    const options = {
      key: fs.readFileSync(process.env.SSL_KEY),
      cert: fs.readFileSync(process.env.SSL_CERT),
      ca: fs.readFileSync(process.env.SSL_CA),
    };
    // https 서버를 만들고 실행시킵니다
    baseServer = https.createServer(options, app)

  }
  else {
    baseServer = http.createServer({}, app)
  }

  

  baseServer.listen(process.env.PORT, () => {
    console.log(`server run at : ${process.env.PORT}`)

    const protocol = process.env.SSL === 'True' ? 'https' : 'http';
    const host = process.env.HOST || 'localhost'; // .env에 HOST 설정이 없는 경우 기본값은 'localhost'
    const port = process.env.PORT;

    console.log(`server running at: ${protocol}://${host}:${port}`);
  });


}

main();