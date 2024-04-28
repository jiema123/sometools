xbot 代理解决无外网的情况，如果客户使用的是一台内网的个人PC, xbot 需要跟 该插件进行 ws 长链接。
该插件需要部署在一台有外网ip的服务器中


直接运行即可，默认端口8080，如需改端口，可以在同目录下新建.env文件修改配置

PORT=XXXX
xbot 的 .env 需要配置上 WS_SERVER ，对应地址为 ws://xxxxx:8080/ws

接口地址为 http://xxxxx:8080/api


go 打包命令
#### linux amd64
GOOS=linux GOARCH=amd64 go build -o xbot-ws-server ./

#### mac amd64 
GOOS=darwin GOARCH=amd64 go build -o xbot-ws-server ./


#### linux x86
GOOS=linux GOARCH=386 go build -o xbot-ws-server ./

#### mac x86
GOOS=darwin GOARCH=386 go build -o xbot-ws-server ./

