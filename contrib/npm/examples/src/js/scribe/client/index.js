class ScribeClient {
  constructor(transportFn) {
    this.transport = transportFn;
  }

  log(data) {
    this.transport(data);
  } 
}

export default ScribeClient;
