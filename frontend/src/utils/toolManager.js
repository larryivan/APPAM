// 工具管理器
class ToolManager {
  constructor() {
    this.tools = [];
    this.currentParameters = {}; // 当前工具页面的参数状态
    this.currentToolInfo = null; // 当前工具信息
    this.loadTools();
  }

  async loadTools() {
    try {
      const response = await fetch('/api/tools');
      const data = await response.json();
      if (data.success) {
        this.tools = data.tools;
      }
    } catch (error) {
      console.error('Error loading tools:', error);
    }
  }

  getToolByName(name) {
    return this.tools.find(tool => 
      tool.tool_name.toLowerCase() === name.toLowerCase()
    );
  }

  getAllTools() {
    return this.tools;
  }

  async suggestTool(query) {
    try {
      const response = await fetch('/api/tools/suggest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });
      const data = await response.json();
      return data.success ? data.suggestion : null;
    } catch (error) {
      console.error('Error suggesting tool:', error);
      return null;
    }
  }

  getToolCategories() {
    const categories = {};
    this.tools.forEach(tool => {
      const category = this.categorize(tool);
      if (!categories[category]) {
        categories[category] = [];
      }
      categories[category].push(tool);
    });
    return categories;
  }

  categorize(tool) {
    const name = tool.tool_name.toLowerCase();
    const desc = tool.description.toLowerCase();
    
    if (name.includes('qc') || desc.includes('quality')) {
      return 'Quality Control';
    } else if (desc.includes('align') || desc.includes('mapping')) {
      return 'Alignment';
    } else if (desc.includes('assembl')) {
      return 'Assembly';
    } else if (desc.includes('annotation')) {
      return 'Annotation';
    } else if (desc.includes('classification') || desc.includes('taxonomic')) {
      return 'Classification';
    } else if (desc.includes('visualization')) {
      return 'Visualization';
    } else {
      return 'Other';
    }
  }

  // 获取当前页面的工具信息
  getCurrentToolInfo() {
    const path = window.location.pathname;
    const toolMatch = path.match(/\/tool\/([^\/]+)/);
    if (toolMatch) {
      const toolName = toolMatch[1];
      return this.getToolByName(toolName);
    }
    return null;
  }

  // 获取当前工具的参数结构
  getCurrentToolParameters() {
    const tool = this.getCurrentToolInfo();
    if (tool && tool.parameters) {
      return tool.parameters.reduce((acc, param) => {
        acc[param.name] = {
          type: param.type,
          description: param.description,
          required: param.required || false,
          default: param.default || '',
          multiple: param.multiple || false,
          extensions: param.extensions || []
        };
        return acc;
      }, {});
    }
    return {};
  }
}

export default new ToolManager();
