// 知识图谱可视化核心逻辑

class KnowledgeGraphVisualizer {
    constructor() {
        this.width = window.innerWidth - 320;
        this.height = window.innerHeight;
        this.data = null;
        this.simulation = null;
        this.svg = null;
        this.g = null;
        this.zoom = null;
        
        // 颜色配置
        this.colors = {
            7: '#00d4ff',  // 七年级 - 青色
            8: '#7b2ff7',  // 八年级 - 紫色
            9: '#ff6b6b'   // 九年级 - 红色
        };
        
        this.init();
    }
    
    init() {
        // 创建 SVG
        this.svg = d3.select('#graph-container')
            .append('svg')
            .attr('width', this.width)
            .attr('height', this.height);
        
        // 添加缩放功能
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                this.g.attr('transform', event.transform);
            });
        
        this.svg.call(this.zoom);
        
        // 创建主容器
        this.g = this.svg.append('g');
        
        // 定义箭头标记
        this.defineArrowMarkers();
        
        // 加载数据
        this.loadData();
        
        // 绑定事件
        this.bindEvents();
    }
    
    defineArrowMarkers() {
        // 前置依赖箭头
        this.svg.append('defs').append('marker')
            .attr('id', 'arrow-prerequisite')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 20)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#00d4ff');
        
        // 逻辑推导箭头
        this.svg.append('defs').append('marker')
            .attr('id', 'arrow-derived')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 20)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#7b2ff7');
        
        // 包含关联箭头
        this.svg.append('defs').append('marker')
            .attr('id', 'arrow-contains')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 20)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#ff6b6b');
    }
    
    async loadData() {
        try {
            // 加载知识图谱数据
            const response = await fetch('knowledge_graph_data.json');
            this.data = await response.json();
            
            // 更新统计
            this.updateStats();
            
            // 渲染图谱
            this.render();
        } catch (error) {
            console.error('加载数据失败:', error);
            // 使用模拟数据
            this.loadMockData();
        }
    }
    
    loadMockData() {
        // 模拟数据用于演示
        this.data = {
            nodes: [
                { id: '7-1-1', name: '正数和负数', grade: 7, semester: '上', chapter: '第一章 有理数', description: '理解正数、负数的概念' },
                { id: '7-1-2', name: '有理数', grade: 7, semester: '上', chapter: '第一章 有理数', description: '理解有理数的概念' },
                { id: '7-1-3', name: '有理数的加减法', grade: 7, semester: '上', chapter: '第一章 有理数', description: '掌握有理数加减法' },
                { id: '8-1-1', name: '三角形的有关概念', grade: 8, semester: '上', chapter: '第十一章 三角形', description: '理解三角形的概念' },
                { id: '8-2-1', name: '全等三角形', grade: 8, semester: '上', chapter: '第十二章 全等三角形', description: '理解全等三角形的概念' },
                { id: '9-1-1', name: '一元二次方程', grade: 9, semester: '上', chapter: '第二十一章 一元二次方程', description: '理解一元二次方程的概念' },
                { id: '9-2-1', name: '二次函数', grade: 9, semester: '上', chapter: '第二十二章 二次函数', description: '理解二次函数的概念' },
            ],
            edges: [
                { source: '7-1-1', target: '7-1-2', relation: '前置依赖' },
                { source: '7-1-2', target: '7-1-3', relation: '前置依赖' },
                { source: '8-1-1', target: '8-2-1', relation: '前置依赖' },
                { source: '9-1-1', target: '9-2-1', relation: '逻辑推导' },
            ]
        };
        
        this.updateStats();
        this.render();
    }
    
    updateStats() {
        document.getElementById('total-nodes').textContent = this.data.nodes.length;
        document.getElementById('total-edges').textContent = this.data.edges.length;
        
        // 统计章节数
        const chapters = new Set(this.data.nodes.map(n => n.chapter));
        document.getElementById('total-chapters').textContent = chapters.size;
        
        // 统计公式数（如果有）
        const formulas = this.data.nodes.reduce((sum, n) => sum + (n.formulas?.length || 0), 0);
        document.getElementById('total-formulas').textContent = formulas;
    }
    
    render() {
        // 清空现有内容
        this.g.selectAll('*').remove();
        
        // 创建力导向图
        this.simulation = d3.forceSimulation(this.data.nodes)
            .force('link', d3.forceLink(this.data.edges).id(d => d.id).distance(150))
            .force('charge', d3.forceManyBody().strength(-500))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide().radius(40));
        
        // 绘制边
        const links = this.g.append('g')
            .selectAll('line')
            .data(this.data.edges)
            .enter()
            .append('line')
            .attr('class', d => `link ${this.getRelationClass(d.relation)}`)
            .attr('stroke-width', 2)
            .attr('marker-end', d => `url(#arrow-${this.getRelationClass(d.relation)})`);
        
        // 绘制节点
        const nodes = this.g.append('g')
            .selectAll('g')
            .data(this.data.nodes)
            .enter()
            .append('g')
            .attr('class', 'node')
            .call(this.drag())
            .on('click', (event, d) => this.showNodeDetail(d))
            .on('mouseover', (event, d) => this.showTooltip(event, d))
            .on('mouseout', () => this.hideTooltip());
        
        // 节点圆圈
        nodes.append('circle')
            .attr('r', 25)
            .attr('fill', d => this.colors[d.grade])
            .attr('stroke', d => this.colors[d.grade])
            .attr('stroke-opacity', 0.5);
        
        // 节点文字
        nodes.append('text')
            .attr('dy', 4)
            .attr('text-anchor', 'middle')
            .attr('fill', '#fff')
            .text(d => d.name.length > 4 ? d.name.substring(0, 4) + '...' : d.name);
        
        // 更新位置
        this.simulation.on('tick', () => {
            links
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            nodes.attr('transform', d => `translate(${d.x},${d.y})`);
        });
    }
    
    getRelationClass(relation) {
        const map = {
            '前置依赖': 'prerequisite',
            '逻辑推导': 'derived',
            '包含关联': 'contains'
        };
        return map[relation] || 'prerequisite';
    }
    
    drag() {
        return d3.drag()
            .on('start', (event, d) => {
                if (!event.active) this.simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            })
            .on('drag', (event, d) => {
                d.fx = event.x;
                d.fy = event.y;
            })
            .on('end', (event, d) => {
                if (!event.active) this.simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            });
    }
    
    showNodeDetail(node) {
        const detail = document.getElementById('node-detail');
        detail.classList.remove('hidden');
        
        document.getElementById('detail-name').textContent = node.name;
        document.getElementById('detail-chapter').textContent = `${node.grade}年级${node.semester}册 · ${node.chapter}`;
        document.getElementById('detail-description').textContent = node.description || '暂无描述';
        
        // 公式
        const formulasSection = document.getElementById('formulas-section');
        const formulasContent = document.getElementById('detail-formulas');
        if (node.formulas && node.formulas.length > 0) {
            formulasSection.style.display = 'block';
            formulasContent.innerHTML = node.formulas.map(f => 
                `<div class="formula-box">${f}</div>`
            ).join('');
        } else {
            formulasSection.style.display = 'none';
        }
        
        // 关键词
        const keywordsSection = document.getElementById('keywords-section');
        const keywordsContent = document.getElementById('detail-keywords');
        if (node.keywords && node.keywords.length > 0) {
            keywordsSection.style.display = 'block';
            keywordsContent.innerHTML = node.keywords.map(k => 
                `<span class="tag">${k}</span>`
            ).join('');
        } else {
            keywordsSection.style.display = 'none';
        }
        
        // 前置知识
        const prerequisitesSection = document.getElementById('prerequisites-section');
        const prerequisitesContent = document.getElementById('detail-prerequisites');
        const prerequisites = this.data.edges
            .filter(e => e.target.id === node.id && e.relation === '前置依赖')
            .map(e => e.source.name);
        if (prerequisites.length > 0) {
            prerequisitesSection.style.display = 'block';
            prerequisitesContent.innerHTML = prerequisites.map(p => 
                `<span class="tag">${p}</span>`
            ).join('');
        } else {
            prerequisitesSection.style.display = 'none';
        }
        
        // 后续知识
        const derivedSection = document.getElementById('derived-section');
        const derivedContent = document.getElementById('detail-derived');
        const derived = this.data.edges
            .filter(e => e.source.id === node.id)
            .map(e => e.target.name);
        if (derived.length > 0) {
            derivedSection.style.display = 'block';
            derivedContent.innerHTML = derived.map(d => 
                `<span class="tag">${d}</span>`
            ).join('');
        } else {
            derivedSection.style.display = 'none';
        }
        
        // 常见错误
        const mistakesSection = document.getElementById('mistakes-section');
        const mistakesContent = document.getElementById('detail-mistakes');
        if (node.common_mistakes && node.common_mistakes.length > 0) {
            mistakesSection.style.display = 'block';
            mistakesContent.innerHTML = node.common_mistakes.map(m => 
                `<div>• ${m}</div>`
            ).join('');
        } else {
            mistakesSection.style.display = 'none';
        }
    }
    
    showTooltip(event, node) {
        const tooltip = document.getElementById('tooltip');
        tooltip.innerHTML = `
            <strong>${node.name}</strong><br>
            <span style="color: rgba(255,255,255,0.6)">${node.chapter}</span>
        `;
        tooltip.style.left = (event.pageX + 10) + 'px';
        tooltip.style.top = (event.pageY - 10) + 'px';
        tooltip.style.opacity = 1;
    }
    
    hideTooltip() {
        document.getElementById('tooltip').style.opacity = 0;
    }
    
    filterByGrade(grade) {
        if (grade === 'all') {
            this.render();
        } else {
            const filteredNodes = this.data.nodes.filter(n => n.grade === parseInt(grade));
            const nodeIds = new Set(filteredNodes.map(n => n.id));
            const filteredEdges = this.data.edges.filter(e => 
                nodeIds.has(e.source.id || e.source) && nodeIds.has(e.target.id || e.target)
            );
            
            const filteredData = {
                nodes: filteredNodes,
                edges: filteredEdges
            };
            
            this.data = filteredData;
            this.render();
        }
    }
    
    search(keyword) {
        if (!keyword) {
            this.render();
            return;
        }
        
        const matchedNodes = this.data.nodes.filter(n => 
            n.name.includes(keyword) || 
            n.chapter.includes(keyword) ||
            (n.keywords && n.keywords.some(k => k.includes(keyword)))
        );
        
        // 高亮匹配的节点
        this.g.selectAll('.node circle')
            .attr('stroke-width', d => matchedNodes.includes(d) ? 5 : 2)
            .attr('filter', d => matchedNodes.includes(d) ? 'drop-shadow(0 0 10px gold)' : 'none');
    }
    
    bindEvents() {
        // 年级筛选
        document.querySelectorAll('.grade-btn[data-grade]').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.grade-btn[data-grade]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.filterByGrade(btn.dataset.grade);
            });
        });
        
        // 学期筛选
        document.querySelectorAll('.grade-btn[data-semester]').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.grade-btn[data-semester]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                // TODO: 实现学期筛选
            });
        });
        
        // 搜索
        document.getElementById('search-input').addEventListener('input', (e) => {
            this.search(e.target.value);
        });
        
        // 缩放控制
        document.getElementById('zoom-in').addEventListener('click', () => {
            this.svg.transition().call(this.zoom.scaleBy, 1.5);
        });
        
        document.getElementById('zoom-out').addEventListener('click', () => {
            this.svg.transition().call(this.zoom.scaleBy, 0.67);
        });
        
        document.getElementById('reset-view').addEventListener('click', () => {
            this.svg.transition().call(this.zoom.transform, d3.zoomIdentity);
        });
        
        // 窗口大小变化
        window.addEventListener('resize', () => {
            this.width = window.innerWidth - 320;
            this.height = window.innerHeight;
            this.svg.attr('width', this.width).attr('height', this.height);
            this.simulation.force('center', d3.forceCenter(this.width / 2, this.height / 2));
            this.simulation.alpha(1).restart();
        });
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    new KnowledgeGraphVisualizer();
});
