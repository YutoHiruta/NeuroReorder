# 従属グラフ構築と各種並べ替え法に関する処理をまとめたクラス

# ------------------------------------------------------------------
# -----                      ライブラリ定義                     -----
# ------------------------------------------------------------------
import math
# グラフ関連
import networkx as nx
import matplotlib.pyplot as plt
# 自前環境
from base_structure.rulemodel import *


class DependencyGraphModel:

    #=========================================
    #                 初期化
    #=========================================
    def __init__(self,rulelist,packetlist=None,compute_weight=True):

        rule_list = rulelist
        packet_list = packetlist

        if compute_weight:
            if not packetlist is None:
                rulelist.compute_weight(packetlist)

        # 各手法の整列済みリスト（ルール番号のリスト）
        self.sgms_reordered_nodelist = []
        self.hikages_reordered_nodelist = []


        # グラフ構築(ノード)
        Graph = nx.DiGraph()
        for i in range(len(rule_list)):
            Graph.add_node(str(i+1))
        # グラフ構築(エッジ)
        edges = []
        for i in reversed(range(len(rule_list))):
            for j in reversed(range(0,i)):
                # 重複があるならエッジを追加
                if rule_list[j].is_dependent(rule_list[i]):
                    #重複ビット集合を示すビット列
                    overlap_bit_string = rule_list[j].match_packet_bit_string(rule_list[i])
                    mask_num = overlap_bit_string.count("*")
                    color = "r"
                    if mask_num <=24:
                        color = "lightsalmon"
                    elif mask_num >=48:
                        color = "purple"

                    edges.append((i+1,j+1,color))
                    Graph.add_edge(i+1,j+1,color=color)

        # グラフ構築(重みを表現し推移辺を削除したグラフを改めて構築)
        Graph2 = nx.DiGraph()
        for i in range(len(rule_list)):
            if rule_list[i]._weight == 0:
                Graph2.add_node(i+1,color="black",size=1)
            else:
                Graph2.add_node(i+1,color="red",size=rule_list[i]._weight)

        for i in range(len(edges)):
            Graph.remove_edge(edges[i][0],edges[i][1])
            if not nx.has_path(Graph,source=edges[i][0],target=edges[i][1]):
                Graph2.add_edge(edges[i][0],edges[i][1],color=edges[i][2])
            Graph.add_edge(edges[i][0],edges[i][1],color=edges[i][2])

        self.rule_list = rule_list
        # 初期グラフ(これをコピーして計算する)
        self.graph = Graph2

        # 計算用グラフ(このグラフ構造のノードを取り除く)
        self.calculate_graph = self.copied_graph()

        # 手法を適用しグラフから除去したノードリスト
        self.removed_nodelist = []

        self.prepare_hikage_method()

    #=======================================================
    #                      グラフを出力
    #=======================================================
    # dump_type = normal  ->  通常の出力
    # dump_type = caption ->  資料に載せるグラフに適した形式で出力
    def plot_graph(self,file_name="figDump.png",dump_type="normal"):
        # 色とノードサイズをグラフデータとして構築
        node_color = [node["color"] for node in self.graph.nodes.values()]
        edge_color = [edge["color"] for edge in self.graph.edges.values()]
        node_size = [node["size"]*10 for node in self.graph.nodes.values()]

        # グラフを描く
        pos = nx.nx_pydot.pydot_layout(self.graph,prog='dot')
        # 出力設定に応じた処理
        if dump_type == "caption":
            nx.draw_networkx(self.graph,pos,node_color="white",node_size=1000,linewidths=1.0,edgecolors="black")
            # 枠線の除去
            plt.gca().spines['right'].set_visible(False)
            plt.gca().spines['left'].set_visible(False)
            plt.gca().spines['top'].set_visible(False)
            plt.gca().spines['bottom'].set_visible(False)
        else:
            nx.draw_networkx(self.graph,pos,edge_color=edge_color,node_color=node_color,node_size=node_size,font_size=1)

        # 出力
        plt.savefig(file_name)

    def show(self):
        graph = self.create_cutted_graph()

        # グラフを描く
        pos = nx.nx_pydot.pydot_layout(graph,prog='dot')
        nx.draw_networkx(graph,pos)
        # 出力
        plt.show()


    #=======================================================
    #手法で既に取り除かれているノードを除外した従属グラフを返す
    #=======================================================
    def create_cutted_graph(self):
        graph = self.copied_graph()
        for element in self.removed_nodelist:
            graph.remove_node(element)

        return graph

    #==========================================================
    #ノードがなくなったときに実行、リストを連結して返り値として返す
    #==========================================================
    def complete(self):
        #日景法の整列済みリストは逆順になっているのでリバース
        self.hikages_reordered_nodelist.reverse()
        #リストを連結して新しいリストにする
        reordered_nodelist = self.sgms_reordered_nodelist + self.hikages_reordered_nodelist

        #print(reordered_nodelist)

        ret_rulelist = RuleList()
        for i in range(len(reordered_nodelist)):
            ret_rulelist.append(self.rule_list[reordered_nodelist[i]-1])

        return ret_rulelist

    #=================================================================================
    #=-------------------------------------------------------------------------------=
    #                                 SGM用のサブ関数
    #=-------------------------------------------------------------------------------=
    #=================================================================================
    #=========================================
    # 部分グラフの重み平均を導出
    #=========================================
    # souce -> 部分木の根
    def sum_of_weight_in_subgraph(self,src):

        sum_of_weight = 0
        keys = []
        dict = nx.shortest_path(self.calculate_graph,source=src)

        for key in dict.keys():
            sum_of_weight += self.rule_list[key-1]._weight
            keys.append(key)

        return (sum_of_weight,keys)

    #=======================================================
    # Gの重み平均一覧から対象のGを選択しreturn
    #=======================================================
    # debugをTrueにすると、各Gの重み平均と選択したGを出力
    def decide_choice(self,keys,debug=False):
        _max = 0
        return_key = -1
        is_all_weight_is_zero = True
        for i in keys:
            ret = self.sum_of_weight_in_subgraph(i)
            if debug:
                print("[%4f] "%(ret),end="")

            ave = ret[0] / len(ret[1])
            if ave > _max:
                _max = ave
                return_key = i
                is_all_weight_is_zero = False

        #キーの重みがすべて0の場合は先頭の要素を選択
        if is_all_weight_is_zero:
            if debug:
                print("-> [%4f] "%(keys[0]))
            return keys[0]
        if debug:
            print("-> [%4f] "%(return_key))
        return return_key


    #=================================================================================
    #=-------------------------------------------------------------------------------=
    #                                 SGMを１回だけ実行
    #=-------------------------------------------------------------------------------=
    #=================================================================================
    def single__sub_graph_mergine(self):

        # グラフをコピー
        #copied_graph = self.copied_graph()
        #for element in self.removed_nodelist:
        #    copied_graph.remove_node(element)

        #print(copied_graph.edges())
        _next = list(self.calculate_graph.nodes)

        while True:
            choice = self.decide_choice(_next)
            _next = list(self.calculate_graph.succ[choice])
            if len(_next) <= 0:
                #print("\t|r[%d]|"%(choice))
                self.sgms_reordered_nodelist.append(choice)
                self.removed_nodelist.append(choice)
                self.calculate_graph.remove_node(choice)
                self.delete_from_Ns(choice)
                #print(choice)
                #_next = list(self.graph.nodes)
                return choice
            #print("")

        return


    # グラフをコピー
    def copied_graph(self):
        ret_graph = nx.DiGraph()
        for node in list(self.graph.nodes):
            ret_graph.add_node(node)


        for edge in list(self.graph.edges):
            ret_graph.add_edge(edge[0],edge[1])


        return ret_graph


#=================================================================================
#=-------------------------------------------------------------------------------=
#                               日景法用のサブ関数
#=-------------------------------------------------------------------------------=
#=================================================================================

    #=======================================================
    # 従属グラフを連結成分へ分解
    #=======================================================
    def subgraph_nodesets(self,graph):
        subgraph_nodesets = []
        evallist = list(graph.nodes)
        #print(evallist)
        while len(evallist) > 0:
            dumplist = []
            pre_evals = []
            pre_evals.append(evallist[0])
            pre_evals += list(nx.all_neighbors(graph,evallist[0]))
            #print(pre_evals)
            while(len(pre_evals) > 0):
                # 先頭を取り出して評価対象とし、評価済みリストへ格納
                target_id = pre_evals.pop(0)
                dumplist.append(target_id)
                # 頂点集合を導出
                vertexs = list(nx.all_neighbors(graph,target_id))
                #print(vertexs)
                # 評価済みの頂点は除外
                new_evals = [vertex for vertex in vertexs if not vertex in dumplist]
                dumplist += new_evals
                pre_evals += new_evals
                #print("PREEVAL",end="")
                #print(pre_evals)
            subgraph_nodesets.append(list(set(dumplist)))
            evallist = [element for element in evallist if not element in dumplist]
        return subgraph_nodesets

    #=======================================================
    # 各連結成分のノードを整列し二次元配列Nsとして返す
    #=======================================================
    """
    def alignment_subgraph_nodesets(self,subgraph_nodesets,subgraph_nodesets_w,copied_graph):
        # 連結成分内の順序を表すリストN(に重みを付加したタプル)の生成
        Ns = []
        for subgraph_nodeset,subgraph_nodeset_w in zip(subgraph_nodesets,subgraph_nodesets_w):
            #cachelist = subgraph_nodeset #頂点集合
            N = []
            #print("<",end="")
            while len(subgraph_nodeset) > 0:
                # 現時点で入次数が0なノード番号を抽出
                matchedlist = [(i,self.rule_list[i-1]._weight) for i in subgraph_nodeset if len(list(self.graph.pred[i])) == 0]
                # 抽出したノード番号に対応する重みリスト
                #matchedlist_w = [subgraph_nodeset_w[i] for i in range(len(subgraph_nodeset)) if subgraph_nodeset[i] in matchedlist]
                #print(matchedlist_w)

                matchedlist.sort(key=lambda x:x[1])
                matchedlist.reverse()
                for element in matchedlist:
                    N.append(element)
                    self.graph.remove_node(element[0])
                    subgraph_nodeset.remove(element[0])

            Ns.append(N)
            #print(">",end="")
        print(Ns)
        #print("")
        return Ns
    """
    def alignment_subgraph_nodesets(self,subgraph_nodesets,subgraph_nodesets_w,copied_graph):
        Ns = []

        for subgraph_nodeset,subgraph_nodeset_w in zip(subgraph_nodesets,subgraph_nodesets_w):
            N = []
            appended_list = []
            # 入次数0のノードを計算
            #print("<",end="")
            matchedlist = [i for i in subgraph_nodeset if len(list(copied_graph.pred[i])) == 0]
            N.append(matchedlist)
            #print(matchedlist,end="")
            #print(">",end="")

            #for x in matchedlist:
            #    print("(%d %d)"%(x,self.rule_list[x-1]._weight),end="")
            appended_list += matchedlist
            for element in matchedlist:
                subgraph_nodeset.remove(element)
            """
            print("")
            print("AdL -> ",end="")
            print(appended_list)
            print("SgNs-> ",end="")
            print(subgraph_nodeset)
            """
            # 入次数1以上のノードを計算
            while(len([x for x in subgraph_nodeset if not x in appended_list]) > 0):
                #print("<",end="")
                matchedlist = [x for x in subgraph_nodeset if len([i for i in list(copied_graph.pred[x]) if not i in appended_list]) == 0 and not x in appended_list]
                N.append(matchedlist)
                #print(matchedlist,end="")
                #print(">",end="")
                #for x in matchedlist:
                #    print("(%d %d)"%(x,self.rule_list[x-1]._weight),end="")

                appended_list += matchedlist

                """
                print("")
                print("AdL -> ",end="")
                print(appended_list)
                print("SgNs-> ",end="")
                print(subgraph_nodeset)
                """


            # 重みを付加したタプルにし、並べ替え

            for i in range(len(N)):
                for j in range(len(N[i])):
                    #print(" %d "%self.rule_list[N[i][j]-1]._weight,end="")
                    N[i][j] = (N[i][j],self.rule_list[N[i][j]-1]._weight)
                N[i].sort(key=lambda x:x[1])
                N[i].reverse()
            # ネストを展開
            N.reverse()
            N = [element for set in N for element in set]
            #print(N,end="")
            Ns.append(N)
        #print(Ns)
        #print("")
        return Ns




    #=======================================================
    # 日景法の準備（従属グラフを連結成分へ分解し整列したクラス変数を用意）
    # インスタンスを生成した際に１回だけ実行する
    #=======================================================
    def prepare_hikage_method(self):
        # グラフをコピー
        copied_graph = self.copied_graph()

        subgraph_nodesets = self.subgraph_nodesets(copied_graph)
        subgraph_nodesets_w = self.subgraph_nodesets(copied_graph)
        for subgraph_nodeset in subgraph_nodesets_w:
            for i in range(len(subgraph_nodeset)):
                subgraph_nodeset[i] = self.rule_list[subgraph_nodeset[i]-1]._weight
        #print("SUBGRAPH NODESETS")
        #print(subgraph_nodesets)
        #print(subgraph_nodesets_w)

        self.Ns = self.alignment_subgraph_nodesets(subgraph_nodesets,subgraph_nodesets_w,copied_graph)
        # すべてのノードのN上の位置を示す辞書
        self.nodepositions_inNs = dict()
        # 辞書に位置情報を追加
        for i in range(len(self.Ns)):
            for j in range(len(self.Ns[i])):
                self.nodepositions_inNs[self.Ns[i][j][0]] = [i,j]
        #print("Ns = ",end="")
        #print(self.Ns)
        #print(self.nodepositions_inNs.items())

    def update_Ns(self,index):
        # 更新後のN

        updated_N = []
        for i in reversed(range(len(self.Ns[index]))):
            updated_N.append((self.Ns[index][i][0],self.Ns[index][i][1]))
        #print("UPDATED_N =",end="")
        #print(updated_N)
        updated_N.reverse()

        for i in range(len(updated_N)):
            self.nodepositions_inNs[updated_N[i][0]] = [index,i]

        self.Ns[index] = updated_N

    def delete_from_Ns(self,index):
        del self.Ns[self.nodepositions_inNs[index][0]][self.nodepositions_inNs[index][1]]
        self.update_Ns(self.nodepositions_inNs[index][0])
        del self.nodepositions_inNs[index]

#=================================================================================
#=-------------------------------------------------------------------------------=
#                               日景法を１回だけ実行
#=-------------------------------------------------------------------------------=
#=================================================================================
    def single__hikage_method(self):

        subgraph_nodesets = self.subgraph_nodesets(self.calculate_graph)
        subgraph_nodesets_w = self.subgraph_nodesets(self.calculate_graph)
        for subgraph_nodeset in subgraph_nodesets_w:
            for i in range(len(subgraph_nodeset)):
                subgraph_nodeset[i] = self.rule_list[subgraph_nodeset[i]-1]._weight

        Ns = self.Ns
        #Ns = self.alignment_subgraph_nodesets(subgraph_nodesets,subgraph_nodesets_w,self.calculate_graph)

        ### Wを計算する
        Ws = []
        for N in Ns:
            w = []
            for i in reversed(range(len(N))):
                w.append(sum([N[j][1] for j in reversed(range(i,len(N)))]) / (len(N)-i))
            #print(w)
            w.reverse()
            Ws.append(w)

        #print("Ns = ",end="")
        #print(self.Ns)

        #print("Ws = ",end="")
        #print(Ws)


        ### 整列済みリストへ挿入するリストの先端位置の決定

        # 重みの最小値リストを構築
        minimum_weights = [min(W) for W in Ws if len(W)]
        #print(minimum_weights)

        #Ns全体で最小の重みの値
        whole_minimum_weight = min(minimum_weights)

        #添字番号を決定
        index_Ns = [min(W) if len(W) > 0 else -1 for W in Ws].index(whole_minimum_weight)
        #print(self.Ns[index_Ns],whole_minimum_weight,index_Ns)
        index_N = len(Ws[index_Ns]) - 1
        for element in reversed(range(len(Ws[index_Ns]))):
            if element == whole_minimum_weight:
                break
            index_N -= 1
        else:
            AssertionError("最小値がNにありません.")



        #print(index_Ns,index_N)

        ### 整列済みリストへ挿入し、該当個所をNsから削除

        addlist = Ns[index_Ns][index_N:]
        addlist.reverse()

        #print(addlist)

        for element in addlist:
            self.hikages_reordered_nodelist.append(element[0])
            self.removed_nodelist.append(element[0])
            self.calculate_graph.remove_node(element[0])
            self.delete_from_Ns(element[0])

        return [element[0] for element in addlist]
