// Optional local integration engine. This is not PostgreSQL16 Docker validation.
import {PGlite} from '@electric-sql/pglite';
import {PGLiteSocketServer} from '@electric-sql/pglite-socket';
const db=await PGlite.create(process.argv[2]||'memory://');
const server=new PGLiteSocketServer({db,host:'127.0.0.1',port:55432,maxConnections:10});
await server.start();
console.log('Validation only: PostgreSQL WASM at 127.0.0.1:55432; production Docker target remains PostgreSQL16');
process.on('SIGINT',async()=>{await server.stop();await db.close();process.exit(0);});
