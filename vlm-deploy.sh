# export HCCL_IF_BASE_PORT=61000 # HCCL master port to communicate with workers. https://www.hiascend.com/document/caselibrary/detail/ptacase_0043
source /usr/local/Ascend/ascend-toolkit/set_env.sh
source /usr/local/Ascend/nnal/atb/set_env.sh
export VLLM_VERSION="0.11.1"
export ASCEND_RT_VISIBLE_DEVICES=7
export VLLM_LOGGING_LEVEL=INFO

model_path="/data/models/MinerU2.5-2509-1.2B"
model_name=$(basename $model_path)
echo "deploy model: $model_name"

##### hccl config #####
nic_name=enp67s0f0np0
local_ip=$(hostname -I | awk '{print $1}')

export HCCL_IF_IP=$local_ip
export GLOO_SOCKET_IFNAME=$nic_name
export TP_SOCKET_IFNAME=$nic_name
export HCCL_SOCKET_IFNAME=$nic_name
export OMP_PROC_BIND=false
export OMP_NUM_THREADS=100
export VLLM_USE_V1=1
export HCCL_BUFFSIZE=512 # HCCL_BUFFSIZE use NPU memory
##### hccl config #####

VLLM_HOST_IP=$(hostname -I | awk '{print $1}')
##### distributed config #####
#quantization=ascend
tensor_parallel=1
enable_expert_parallel=false # if true, expert parallel sharded into size=$tensor_parallel

pipe_parallel=false
pipe_parallel_size=2

data_parallel=false
data_parallel_size=4 # global data parallel size
data_parallel_size_local=2 # data parallel in one node
root_node=true
data_parallel_address=$local_ip
data_parallel_rpc_port=13389
data_parallel_start_rank=2
##### distributed config #####

##### ascend extra config #####
additional_config='{"ascend_scheduler_config":{"enabled":false},"torchair_graph_config":{"enabled":false}}'
no_enable_prefix_caching=true
##### ascedn extra config #####

dtype=bfloat16
kvcache_blocks_fraction=0.96 # minimum ratio with graph mode
max_model_len=16384
max_num_seqs=64 # max batch of seqs, wait queue+infer queue+swap queue
# tokenizer_pool_size=4
max_num_batched_tokens=$(($max_model_len*32)) # Maximum number of (batched) tokens to be processed in a single iteration.

# errors occurred as follows: f"Attempted to assign {expr} = {flattened.shape[0]} multimodal tokens to {num_expected_tokens} placeholders")
# when enable chunked prefill
enable_chunked_prefill=false
eager_mode=false

### visual LLM preprocessor config ###
# max_pixels=$((2048*2048))
# mm_processor_kwargs='{"max_pixels": 4194304}'
# limit_mm_per_prompt="image=1,video=0"
### visual LLM preprocessor config ###

enable_tool_choice=false
tool_call_parser=hermes
enable_reasoning=false
reasoning_parser=deepseek_r1
nothink_jinja_file=/data/models/Qwen3-30B-A3B-Instruct-2507/qwen3_nonthinking.jinja

### vllm extra config ###
logits_processors="mineru_vl_utils.logits_processor.vllm_v1_no_repeat_ngram:VllmV1NoRepeatNGramLogitsProcessor"
### vllm extra config ###


### torch && torch_npu config ###
# Upper limit of memory block splitting allowed (MB), Setting this parameter can prevent large memory blocks from being split.
export PYTORCH_NPU_ALLOC_CONF="max_split_size_mb:250"

# When operators on the communication stream have dependencies, they all need to be ended before being released for reuse.
# The logic of multi-stream reuse is to release the memory on the communication stream in advance so that the computing stream can be reused.
export PYTORCH_NPU_ALLOC_CONF="expandable_segments:True"
### torch && torch_npu config ###

cmd="vllm serve $model_path\
  --served-model-name $model_name\
  --dtype $dtype\
  --tensor-parallel-size $tensor_parallel\
  --gpu-memory-utilization $kvcache_blocks_fraction\
  --max-model-len $max_model_len\
  --max-num-seqs $max_num_seqs\
  --host '0.0.0.0'\
  --port 9001"

if [[ $data_parallel == 'true' ]];then
        echo "[data parallel enabled]"
        cmd="$cmd --data-parallel-size $data_parallel_size --data-parallel-size-local $data_parallel_size_local"
        if [[ $root_node == 'false' ]];then
                echo "[worker node] dp address should not be worker ip"
                if [[ $data_parallel_address == $local_ip ]];then
                        echo "[worker data parallel ip check failed]"
                        echo "you need to config data_parallel_address to be root node ip"
                        exit 1
                fi
                echo "[worker node] dp ip address looks good"
                cmd="$cmd --headless"
                cmd="$cmd --data-parallel-start-rank $data_parallel_start_rank"
        fi
        cmd="$cmd --data-parallel-address $data_parallel_address --data-parallel-rpc-port $data_parallel_rpc_port"
fi

if [[ $enable_expert_parallel == 'true' ]];then
        echo "[expert parallel enabled]"
        cmd="$cmd --enable-expert-parallel"
fi

if [[ $VLLM_USE_V1 == 1 ]];then
        echo "[VLLM V1 engine enabled] ascend additional setting needed"
        cmd="$cmd --no-enable-prefix-caching"
        cmd="$cmd --additional-config '$additional_config'"
fi

if [[ $pipe_parallel == 'true' ]];then
        echo "[pipeline parallel enabled] $pipe_parallel_size"
        # Pipeline parallelism currently requires AsyncLLMEngine, hence the --disable-frontend-multiprocessing is set.
        # https://vllm-ascend.readthedocs.io/en/main/tutorials/multi_node.html
        cmd="$cmd --pipeline-parallel-size $pipe_parallel_size"
fi


if [[ $enable_tool_choice == "true" ]]; then
        echo "tool choice enabled, using tool call parser: $tool_call_parser"
        cmd="$cmd --enable-auto-tool-choice --tool-call-parser $tool_call_parser"
        if [[ $enable_reasoning == 'true' ]]; then
                echo "tool choice cannot be used with reasoning enabled, set reasoning to false."
                enable_reasoning=false
        fi
fi

if [[ $enable_reasoning == "true" ]]; then
        if [[ $reasoning_parser == "null" ]]; then
                echo "reasoning_parser must not be null while enable reasoning"
                exit 1
        else
                cmd="$cmd --enable-reasoning --reasoning-parser $reasoning_parser"
        fi
else
	if [[ -v nothink_jinja_file ]];then
                if [[ -e $nothink_jinja_file ]];then
                        cmd="$cmd --chat-template $nothink_jinja_file"
                else
                        echo "$nothink_jinja_file path invalid."
                fi
	else
                echo "you must config nothink_jinja_file if enable_reasoning set to False"
		exit 1
        fi
		
fi

if [[ $enable_chunked_prefill == "true" ]];then
        echo "chunked prefill enabled"
        cmd="$cmd --enable-chunked-prefill"
fi

if [[ -v max_num_batched_tokens ]];then
        echo "max_num_batched_tokens param detected"
        cmd="$cmd --max-num-batched-tokens $max_num_batched_tokens"
fi

if [[ $eager_mode == 'true' ]];then
        echo "eager mode enabled"
        cmd="$cmd --enforce-eager"
fi

if [[ -v quantization ]];then
        echo "[quantization enabled]"
        cmd="$cmd --quantization $quantization"
fi

# if [[ $model_name =~ "VL" ]];then
#         echo "VLM deployed detected, preprocessor config override"
#         cmd="$cmd --mm_processor_kwargs $mm_processor_kwargs"
# fi

cmd="$cmd --logits-processors $logits_processors"


echo -e "\e[31mpreview command: $cmd\e[0m"
eval $cmd
