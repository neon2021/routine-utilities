# requirements

```shell
faster-whisper==1.1.1
ctranslate2==4.4.0 # supports cuDNN 8.x
```


```shell
ldconfig -p|grep libcudnn                               
	libcudnn_ops_train.so.8 (libc6,x86-64) => /usr/local/cuda/targets/x86_64-linux/lib/libcudnn_ops_train.so.8
	libcudnn_ops_train.so (libc6,x86-64) => /usr/local/cuda/targets/x86_64-linux/lib/libcudnn_ops_train.so
	libcudnn_ops_infer.so.8 (libc6,x86-64) => /usr/local/cuda/targets/x86_64-linux/lib/libcudnn_ops_infer.so.8
	libcudnn_ops_infer.so (libc6,x86-64) => /usr/local/cuda/targets/x86_64-linux/lib/libcudnn_ops_infer.so
	libcudnn_cnn_train.so.8 (libc6,x86-64) => /usr/local/cuda/targets/x86_64-linux/lib/libcudnn_cnn_train.so.8
	libcudnn_cnn_train.so (libc6,x86-64) => /usr/local/cuda/targets/x86_64-linux/lib/libcudnn_cnn_train.so
	libcudnn_cnn_infer.so.8 (libc6,x86-64) => /usr/local/cuda/targets/x86_64-linux/lib/libcudnn_cnn_infer.so.8
	libcudnn_cnn_infer.so (libc6,x86-64) => /usr/local/cuda/targets/x86_64-linux/lib/libcudnn_cnn_infer.so
	libcudnn_adv_train.so.8 (libc6,x86-64) => /usr/local/cuda/targets/x86_64-linux/lib/libcudnn_adv_train.so.8
	libcudnn_adv_train.so (libc6,x86-64) => /usr/local/cuda/targets/x86_64-linux/lib/libcudnn_adv_train.so
	libcudnn_adv_infer.so.8 (libc6,x86-64) => /usr/local/cuda/targets/x86_64-linux/lib/libcudnn_adv_infer.so.8
	libcudnn_adv_infer.so (libc6,x86-64) => /usr/local/cuda/targets/x86_64-linux/lib/libcudnn_adv_infer.so
	libcudnn.so.8 (libc6,x86-64) => /usr/local/cuda/targets/x86_64-linux/lib/libcudnn.so.8
	libcudnn.so (libc6,x86-64) => /usr/local/cuda/targets/x86_64-linux/lib/libcudnn.so
```